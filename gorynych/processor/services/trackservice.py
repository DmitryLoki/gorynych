# coding=utf-8
from collections import defaultdict
import time
import cPickle

from twisted.python import log
from twisted.internet import threads, defer, task

from gorynych.common.domain import events
from gorynych.common.exceptions import NoGPSData
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import TrackArchive, track
from gorynych.common.application import EventPollingService
from gorynych.common.domain.services import APIAccessor

from gorynych.receiver.receiver import RabbitMQService

API = APIAccessor()

class A:
    def process_data(self, data):
        pass

    def append_data(self, data):
        pass

ADD_TRACK_TO_GROUP = """
    INSERT INTO TRACKS_GROUP(group_id, track_id, track_label) VALUES (%s,
        (SELECT ID FROM TRACK WHERE TRACK_ID=%s), %s);
"""


class ProcessorService(EventPollingService):
    '''
    Orchestrate track creation and parsing.
    '''
    @defer.inlineCallbacks
    def process_ArchiveURLReceived(self, ev):
        '''
        Download and process track archive.
        '''
        race_id = ev.aggregate_id
        url = ev.payload
        log.msg("URL received ", url)
        res = yield defer.maybeDeferred(API.get_track_archive, str(race_id))
        if res and res['status'] == 'no archive':
            ta = TrackArchive(str(race_id), url)
            log.msg("Start unpacking archive %s for race %s" % (url, race_id))
            archinfo = yield threads.deferToThread(ta.process_archive)
            yield self._inform_about_paragliders(archinfo, race_id)
        yield self.event_dispatched(ev.id)

    def _inform_about_paragliders(self, archinfo, race_id):
        '''
        Inform system about finded paragliders, then inform system about
        succesfull archive unpacking.
        @param archinfo: ([{person_id, trackfile, contest_number}],
        [trackfile,], [person_id,])
        @type race_id: C{str}
        '''
        # TODO: add events for extra tracks and left paragliders.
        tracks, extra_tracks, left_paragliders = archinfo
        dlist = []
        es = pe.event_store()
        for di in tracks:
            ev = events.ParagliderFoundInArchive(race_id, payload=di, aggregate_type='race')
            dlist.append(es.persist(ev))
        d = defer.DeferredList(dlist, fireOnOneErrback=True)
        d.addCallback(lambda _:es.persist(events
                .TrackArchiveUnpacked(race_id, payload=archinfo, aggregate_type='race')))
        d.addCallback(lambda _:log.msg("Track archive for race %s unpacked"
                                       % race_id))
        return d

    @defer.inlineCallbacks
    def process_RaceGotTrack(self, ev):
        race_id = ev.aggregate_id
        track_id = ev.payload['track_id']
        cn = ev.payload.get('contest_number')
        group_id = str(race_id)
        if ev.payload['track_type'] == 'online':
            group_id = group_id + '_online'
        try:
            log.msg(">>>Adding track %s to group %s <<<" % (track_id,
                                                                group_id))
            yield self.pool.runOperation(ADD_TRACK_TO_GROUP, (group_id,
                track_id, cn))
        except Exception as e:
            log.msg("Track %s hasn't been added to group %s because of %r" %
                    (track_id, group_id, e))
        if ev.payload['track_type'] == 'online':
            defer.returnValue('')
        res = yield defer.maybeDeferred(API.get_track_archive, str(race_id))
        if res:
            processed = len(res['progress']['parsed_tracks']) + len(
                res['progress']['unparsed_tracks'])
        if res and len(res['progress']['paragliders_found']) == processed and not (
                res['status'] == 'parsed'):
            yield pe.event_store().persist(events.TrackArchiveParsed(
                race_id, aggregate_type='race'))
        yield self.event_dispatched(ev.id)


class TrackService(EventPollingService):
    '''
    TrackService parse track archive.
    '''

    def __init__(self, pool, event_store, track_repository):
        EventPollingService.__init__(self, pool, event_store)
        self.aggregates = dict()
        self.track_repository = track_repository

    def process_ParagliderFoundInArchive(self, ev):
        '''
        After this message TrackService start to listen events for this
         track.
        '''
        trackfile = ev.payload['trackfile']
        person_id = ev.payload['person_id']
        contest_number = ev.payload['contest_number']
        log.msg("Got trackfile for paraglider %s" % person_id)
        race_id = ev.aggregate_id
        try:
            race_task = API.get_race_task(str(race_id))
        except Exception as e:
            log.msg("Error in API call: %r" % e)
            race_task = None
        if not isinstance(race_task, dict):
            log.msg("Race task wasn't received from API: %r" % race_task)
            defer.returnValue('')
        track_type = 'competition_aftertask'
        track_id = track.TrackID()

        tc = events.TrackCreated(track_id)
        tc.payload = dict(race_task=race_task, track_type=track_type)
        def no_altitude_failure(failure):
            failure.trap(NoGPSData)
            log.err("Track %s don't has GPS altitude" % contest_number)
            ev = events.TrackWasNotParsed(race_id, aggregate_type='race')
            ev.payload = dict(contest_number=contest_number,
                reason=failure.getErrorMessage())
            d = self.event_store.persist(ev)
            return d

        log.msg("Start creating track %s for paraglider %s" % (track_id, person_id))

        t = track.Track(track_id, [tc])
        t.changes.append(tc)
        try:
            t.append_data(trackfile)
            t.process_data()
        except Exception as e:
            ev = events.TrackWasNotParsed(race_id, aggregate_type='race')
            ev.payload = dict(contest_number=contest_number,
                reason=repr(e.message))
            d = self.event_store.persist(ev)
            return d

        d = self.persist(t)

        #d = self.event_store.persist(tc)
        #d.addCallback(lambda _:self.execute_ProcessData(track_id, trackfile))
        d.addCallback(lambda _:log.msg("Track %s processed and saved." % contest_number))
        d.addCallback(lambda _:self.append_track_to_race_and_person(race_id,
            track_id, track_type, contest_number, person_id))
        d.addCallback(lambda _:log.msg("track %s events appended" % contest_number))
        d.addErrback(no_altitude_failure)
        d.addCallback(lambda _:self.event_dispatched(ev.id))
        return d

    def execute_ProcessData(self, track_id, data):
        return self.update(track_id, 'process_data', data)

    @defer.inlineCallbacks
    def update(self, aggregate_id, method, *args, **kwargs):
        aggr = yield defer.maybeDeferred(self._get_aggregate, aggregate_id)
        getattr(aggr, method)(*args, **kwargs)
        # Persist points, state and events if any.
        yield self.persist(aggr)

    @defer.inlineCallbacks
    def _get_aggregate(self, _id):
        if not self.aggregates.get(_id):
            elist = yield self.event_store.load_events(_id)
            t = track.Track(_id, events=elist)
            self.aggregates[_id] = t
        defer.returnValue(self.aggregates[_id])

    def append_track_to_race_and_person(self, race_id, track_id, track_type,
            contest_number, person_id):
        '''
        When track is ready to be shown send messages for Race and Person to
         append this track to them.
        '''
        rgt = events.RaceGotTrack(race_id, aggregate_type='race')
        rgt.payload = dict(contest_number=contest_number,
            track_type=track_type, track_id=str(track_id))
        ptc = events.PersonGotTrack(person_id, str(track_id),
            aggregate_type='person')
        log.msg("Append events for track %s" % track_id)
        return self.event_store.persist([rgt, ptc])

    def persist(self, aggr):
        log.msg("Persist aggregate %s" % aggr.id)
        d = self.track_repository.save(aggr)
        return d


class OnlineTrashService(RabbitMQService):
    '''
    receive messages with track data from rabbitmq queue.
    '''

    def __init__(self, pool, repo, **kw):
        RabbitMQService.__init__(self, **kw)
        self.pool = pool
        self.did_aid = {}
        self.repo = repo
        # {race_id:{track_id:Track}}
        self.tracks = defaultdict(dict)
        self.processor = task.LoopingCall(self.process)
        self.processor.start(60, False)
        # device_id:(race_id, contest_number, time)
        self.devices = dict()

    def when_started(self):
        d = defer.Deferred()
        d.addCallback(self.open)
        d.addCallback(lambda x: task.LoopingCall(self.read, x))
        d.addCallback(lambda lc: lc.start(0.00))
        d.callback('rdp')
        return d

    def handle_payload(self, queue_name, channel, method_frame, header_frame,
            body):
        data = cPickle.loads(body)
        if not data.has_key('ts'):
            # ts key MUST be in a data.
            return
        if data['lat'] < 0.1 and data['lon'] < 0.1:
            return
        return self.handle_track_data(data)

    @defer.inlineCallbacks
    def _get_race_by_tracker(self, device_id, t):
        result = self.devices.get(device_id)
        if result and t - result[2] < 300:
            defer.returnValue((result[0], result[1]))
        row = yield self.pool.runQuery(pe.select('current_race_by_tracker',
            'race'),(device_id, t))
        if not row:
            defer.returnValue(None)
        self.devices[device_id] = (row[0][0], row[0][1], int(time.time()))
        defer.returnValue(row[0])

    def handle_track_data(self, data):
        now = int(time.time())
        d = self._get_race_by_tracker(data['imei'], now)
        d.addCallback(self._get_track, data['imei'])
        d.addCallback(lambda tr: tr.append_data(data))
        return d

    def _get_track(self, rid, device_id):
        if not rid:
            # Null-object.
            return A()
        rid, cnumber = rid
        if not cnumber:
            return A()
        if self.tracks.has_key(rid) and self.tracks[rid].has_key(device_id):
            # Race and track are in memory. Return Track for work.
            return self.tracks[rid][device_id]
        else:
            d = self.pool.runQuery(pe.select('track_n_label', 'track'),
                (rid, cnumber))
            d.addCallback(self._restore_or_create_track, rid, device_id, cnumber)
            return d

    @defer.inlineCallbacks
    def _restore_or_create_track(self, row, rid, device_id, contest_number):
        '''
        Отдаёт уже существующий трек, иначе создаёт его, сохраняет события о
         его создании и добавлении в гонку, и отдаёт.

        @param row: (track_type.name, track_id, track.start_time,
        track.end_time, contest_number), может быть пустым если трека ещё не
         существует.
        @type row: C{tuple}
        @return:
        @rtype: C{Track}
        '''
        tracks = self.tracks[rid]
        log.msg("Restore or create track for race %s and device %s" %
                (rid, device_id))
        if row:
            log.msg("Restore track", row[1])
            result = yield self.repo.get_by_id(row[1][1])
        else:
            log.msg("Create new track")
            race_task = API.get_race_task(str(rid))
            if not isinstance(race_task, dict):
                log.msg("Race task wasn't received from API: %r" % race_task)
                defer.returnValue('')
            track_type = 'online'
            track_id = track.TrackID()
            tc = events.TrackCreated(track_id)
            tc.payload = dict(race_task=race_task, track_type=track_type)
            result = track.Track(track_id, [tc])
            rgt = events.RaceGotTrack(rid, aggregate_type='race')
            rgt.payload = dict(contest_number=contest_number,
                track_type=track_type, track_id=str(track_id))
            result.changes.append(rgt)
            yield pe.event_store().persist([tc])
        tracks[device_id] = result
        log.msg("Restored or created track %s for device %s" % (
                    result.id, device_id))
        defer.returnValue(result)

    @defer.inlineCallbacks
    def process(self):
        '''
        Process and save tracks.
        @return:
        @rtype:
        '''
        for rid in self.tracks.keys():
            for key in self.tracks[rid].keys():
                try:
                    self.tracks[rid][key].process_data()
                    yield self.repo.save(self.tracks[rid][key])
                except Exception as e:
                    log.err("%r" % e)
        return

