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
from gorynych.common.domain.services import APIAccessor, SinglePollerService

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
        url = ev.payload['url']
        contest_id = ev.payload['contest_id']
        log.msg("URL received ", url)
        res = yield defer.maybeDeferred(API.get_track_archive, contest_id, str(race_id))
        if res and res['status'] == 'no archive':
            ta = TrackArchive(str(race_id), str(contest_id), url)
            log.msg("Start unpacking archive %s for race %s of contest %s" % (url, race_id, contest_id))
            archinfo = yield threads.deferToThread(ta.process_archive)
            yield self._inform_about_paragliders(archinfo, race_id, contest_id)
        yield self.event_dispatched(ev.id)

    def _inform_about_paragliders(self, archinfo, race_id, contest_id):
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
        contest_id = ev.payload.get('contest_id')
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
        res = yield defer.maybeDeferred(API.get_track_archive, contest_id, str(race_id))
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
        contest_id = ev.payload['contest_id']
        log.msg("Got trackfile for paraglider %s" % person_id)
        race_id = ev.aggregate_id
        try:
            race_task = API.get_race_task(contest_id, str(race_id))
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
        d.addCallback(lambda _:self.append_track_to_race_and_person(contest_id, race_id,
            track_id, track_type, contest_number, person_id))
        d.addCallback(lambda _:log.msg("track %s events appended" % contest_number))
        d.addErrback(no_altitude_failure)
        d.addCallback(lambda _:self.event_dispatched(ev.id))
        return d

    def append_track_to_race_and_person(self, contest_id, race_id, track_id, track_type,
            contest_number, person_id):
        '''
        When track is ready to be shown send messages for Race and Person to
         append this track to them.
        '''
        rgt = events.RaceGotTrack(race_id, aggregate_type='race')
        rgt.payload = dict(contest_number=contest_number,
            track_type=track_type, track_id=str(track_id), contest_id=contest_id)
        ptc = events.PersonGotTrack(person_id, str(track_id),
            aggregate_type='person')
        log.msg("Append events for track %s" % track_id)
        return self.event_store.persist([rgt, ptc])

    def persist(self, aggr):
        log.msg("Persist aggregate %s" % aggr.id)
        d = self.track_repository.save(aggr)
        return d


class OnlineTrashService(SinglePollerService):
    '''
    receive messages with track data from rabbitmq queue.
    '''

    def __init__(self, pool, track_repository, connection, **kw):
        poll_interval = kw.get('interval', 0.0)
        SinglePollerService.__init__(self, connection, poll_interval, queue_name='rdp')
        self.pool = pool
        self.did_aid = {}
        self.repo = track_repository
        # {device_id:Track}
        self.tracks = dict()
        self.processor = task.LoopingCall(self.process)
        # TODO: remove this from constructor.
        self.processor.start(60, False)
        # tracker_id:(contest_id, race_id, contest_number, time)
        self.trackers = dict()

    def handle_payload(self, channel, method_frame, header_frame, body, queue_name):
        data = cPickle.loads(body)
        if not data.has_key('ts'):
            # ts key MUST be in a data.
            return
        if 'event' in data:
            return self.handle_event(data)
        if data['lat'] < 0.1 and data['lon'] < 0.1:
            return
        return self.handle_track_data(data)

    def handle_track_data(self, data):
        d = defer.Deferred()
        tracker_id = '-'.join((data['device_type'], data['imei']))
        if data['device_type'] in ['tr203', 'telt_gh3000', 'gt60',
            'pmtracker', 'pmtracker_sbd']:
            d.addCallback(lambda _: self._get_race_by_tracker(tracker_id))
        d.addCallback(self._get_track, tracker_id)
        d.addCallback(lambda tr: tr.append_data(data))
        d.callback(None)
        return d

    @defer.inlineCallbacks
    def _get_race_by_tracker(self, tracker_id):
        '''
        Return and cache information about current contest race by tracker id.
        @param tracker_id: tracker_id
        @type tracker_id: C{str}
        @return: (contest_id, race_id, contest_number)
        @rtype: C{tuple}
        '''
        now = int(time.time())
        result = self.trackers.get(tracker_id)
        if result and now - result[3] < 300:
            defer.returnValue((result[0], result[1], result[2]))
        contest_id, race_id, cont_num = yield defer.maybeDeferred(
            API.get_current_race_by_tracker, tracker_id)
        self.trackers[tracker_id] = (contest_id, race_id, cont_num, now)
        defer.returnValue((contest_id, race_id, cont_num))

    @defer.inlineCallbacks
    def _get_track(self, row, tracker_id):
        if tracker_id in self.tracks:
            defer.returnValue(self.tracks[tracker_id])
        if not row:
            # Null-object.
            defer.returnValue(A())
        contest_id, rid, cnumber = row
        if not cnumber or not contest_id or not rid:
            defer.returnValue(A())
        row = yield self.pool.runQuery(pe.select('track_n_label',
            'track'), ('_'.join((rid, 'online')), cnumber))
        tr = yield self._restore_or_create_track(row, rid, tracker_id,
            cnumber, contest_id)
        defer.returnValue(tr)

    @defer.inlineCallbacks
    def _restore_or_create_track(self, row, rid, device_id, contest_number,
            contest_id):
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
        log.msg("Restore or create track for race %s and device %s" %
                (rid, device_id))
        if row:
            log.msg("Restore track", row)
            result = yield self.repo.get_by_id(row[0][1])
        else:
            log.msg("Create new track")
            race_task = API.get_race_task(contest_id, str(rid))
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
        self.tracks[device_id] = result
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
        for key in self.tracks.keys():
            try:
                self.tracks[key].process_data()
                yield self.repo.save(self.tracks[key])
            except Exception as e:
                log.err("%r" % e)
        return

    def handle_event(self, data):
        '''
        React on data with event.
        @param data: {ts, event, [track_id], imei}
        @type data: C{dict}
        @return:
        @rtype:
        '''
        if data['event'] == 'TRACK_STARTED':
            return self._handle_track_started(data)
        elif data['event'] == 'TRACK_ENDED':
            return self._handle_track_ended(data)

    @defer.inlineCallbacks
    def _handle_track_started(self, data):
        yield self._handle_track_ended(data)
        track_id, ts = data['track_id'], data['ts']
        tracker_id = '-'.join((data['device_type'], data['imei']))
        track_id = track.TrackID.fromstring(track_id)
        cont_id, race_id, cont_num = yield self._get_race_by_tracker(
            tracker_id)
        if race_id is None:
            # Private tracking.
            tracker_id = '-'.join((data['device_type'], tracker_id))
            tr = yield defer.maybeDeferred(API.get_tracker_owner, tracker_id)\
                .addCallback(self._create_private_track, track_id, ts)
            self.tracks[tracker_id] = tr
            defer.returnValue(None)
        yield self._get_track((cont_id, race_id, cont_num), tracker_id)


    def _create_private_track(self, owner, track_id, ts):
        if owner is None:
            return
        payload = dict(track_type='private',
                        race_task=dict(type='undefined',
                                        start_time=int(ts)))
        tc = events.TrackCreated(track_id, payload=payload, occured_on=ts)
        trs = events.TrackStarted(track_id)
        pgt = events.PersonGotTrack(owner, track_id, occured_on=ts)
        return track.Track(track_id, [tc, trs, pgt])

    def _handle_track_ended(self, data):
        '''
        Check if track ended and delete it from self.tracks. If track isn't
        ended then end it and delete.
        @param data: message from queue.
        @type data: C{dict}
        @return: None
        @rtype: C{defer.Deferred}
        '''
        tracker_id = '-'.join((data['device_type'], data['imei']))
        track_id, ts = data['track_id'], data['ts']
        if not tracker_id in self.tracks:
            return
        d = defer.Deferred()
        old_track = self.tracks[tracker_id]
        if not old_track._state.ended:
            old_track.apply(events.TrackEnded(old_track.id,
                payload={ }, occured_on=ts))
            d.addCallback(self.repo.save)

        def delete_track_from_memory(*args):
            del self.tracks[tracker_id]
            return

        d.addCallback(delete_track_from_memory)
        d.callback(old_track)
        return d

