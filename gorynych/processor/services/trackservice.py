import time

from twisted.python import log
from twisted.internet import threads, defer

from gorynych.common.domain import events
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import TrackArchive, track
from gorynych.common.application import EventPollingService
from gorynych.common.domain.services import APIAccessor
from gorynych import OPTS


API = APIAccessor()

def find_snapshots(item, dbid):
    result = []
    if item.has_key('finish_time'):
        sn = dict(timestamp=int(item['finish_time']),
                  id=long(dbid),
                  snapshot="finished")
        result.append(sn)
    else:
        sn = dict(timestamp=int(item['times'][-1]),
                  id=long(dbid),
                  snapshot="landed")
        result.append(sn)
    return result


class ProcessorService(EventPollingService):
    '''
    Orchestrate track creation and parsing.
    '''
    in_progress = dict()
    ttl = 120
    @defer.inlineCallbacks
    def process_ArchiveURLReceived(self, ev):
        '''
        Download and process track archive.
        '''
        race_id = ev.aggregate_id
        res = yield API.get_track_archive(str(race_id))
        url = ev.payload
        log.msg("URL received ", url)
        if url in self.in_progress and time.time() - self.in_progress[url] <\
                self.ttl:
            # Don't process one url simultaneously.
            defer.returnValue('')
        if res['status'] == 'no archive':
            ta = TrackArchive(str(race_id), url)
            log.msg("Start unpacking archive %s for race %s" % (url, race_id))
            archinfo = yield threads.deferToThread(ta.process_archive)
            yield self._inform_about_paragliders(archinfo, race_id)
        elif res['status'] == 'unpacked':
            yield self.event_dispatched(ev.id)

    def _inform_about_paragliders(self, archinfo, race_id):
        '''
        Inform system about finded paragliders, then inform system about
        succesfull archive unpacking.
        @param archinfo: ([{person_id, trackfile, contest_number}],
        [trackfile,], [person_id,])
        @type race_id: C{RaceID}
        '''
        # TODO: add events for extra tracks and left paragliders.
        tracks, extra_tracks, left_paragliders = archinfo
        dlist = []
        es = pe.event_store()
        for di in tracks:
            ev = events.ParagliderFoundInArchive(race_id, payload=di)
            dlist.append(es.persist(ev))
        d = defer.DeferredList(dlist, fireOnOneErrback=True)
        d.addCallback(lambda _:es.persist(events
                .TrackArchiveUnpacked(race_id, payload=archinfo)))
        d.addCallback(lambda _:log.msg("Track archive for race %s unpacked"
                                       % race_id))
        return d

    @defer.inlineCallbacks
    def process_RaceGotTrack(self, ev):
        race_id = ev.aggregate_id
        res = yield API.get_track_archive(str(race_id))
        if len(res['progress']['parsed_tracks']) == len(res['progress'][
            'paragliders_found']) and not res['status'] == 'parsed':
            yield pe.event_store().persist(events.TrackArchiveParsed(race_id))
        yield self.event_dispatched(ev.id)


class TrackService(EventPollingService):
    '''
    TrackService parse track archive.
    '''
    def __init__(self, event_store, track_repository):
        self.event_store = event_store
        self.aggregates = dict()
        self.track_repository = track_repository

    @defer.inlineCallbacks
    def process_ParagliderFoundInArchive(self, ev):
        '''
        After this message TrackService start to listen events for this
         track.
        @param ev:
        @type ev:
        @return:
        @rtype:
        '''
        trackfile = ev.payload['trackfile']
        person_id = ev.payload['person_id']
        contest_number = ev.payload['contest_number']
        race_id = ev.aggregate_id
        race_task = yield APIAccessor().get_race_task(str(race_id))
        track_type = 'competition_aftertask'
        track_id = track.TrackID()

        tc = events.TrackCreated(track_id)
        tc.payload = dict(race_task=race_task, track_type=track_type)

        d = self.event_store.persist(tc)
        d.addCallback(lambda _:self.execute_ProcessData(track_id, trackfile))
        d.addCallback(lambda _:self.append_track_to_race_and_person(race_id,
            track_id, track_type, contest_number, person_id))
        d.addCallback(lambda _:self.event_dispatched(ev.id))
        yield d

    def execute_ProcessData(self, track_id, data):
        return self.update(track_id, 'process_data', data)

    @defer.inlineCallbacks
    def update(self, aggregate_id, method, eid, *args, **kwargs):
        aggr = yield defer.maybeDeferred(self._get_aggregate, aggregate_id)
        getattr(aggr, method)(*args, **kwargs)
        # Persist points, state and events if any.
        yield self.persist(aggr)

    def _get_aggregate(self, _id):
        if self.aggregates.get(_id):
            return self.aggregates[_id]
        else:
            d = defer.succeed(_id)
            d.addCallback(self.event_store.load_events, _id)
            d.addCallback(lambda s:track.Track(_id, events=s))
            d.addCallback(lambda _ag: self.aggregates.update({_id:_ag}))
            d.addCallback(lambda _:self.aggregates[_id])

    def append_track_to_race_and_person(self, race_id, track_id, track_type,
            contest_number, person_id):
        '''
        When track is ready to be shown send messages for Race and Person to
         append this track to them.
        @param race_id:
        @type race_id:
        @param track_id:
        @type track_id:
        @param track_type:
        @type track_type:
        @param contest_number:
        @type contest_number:
        @param person_id:
        @type person_id:
        @return:
        @rtype:
        '''
        rgt = events.RaceGotTrack(race_id, aggregate_type='race')
        rgt.payload = dict(contest_number=contest_number,
            track_type=track_type, track_id=str(track_id))
        ptc = events.PersonGotTrack(person_id, str(track_id),
            aggregate_type='person')
        return self.event_store.persist([rgt, ptc])

    def persist(self, aggr):
        d = self.event_store.persist(aggr.changes)
        d.addCallback(lambda _:self.track_repository.save(aggr))
        return d


def pic(x, name, suf):
    import cPickle
    try:
        f = open('.'.join((name, suf, 'pickle')), 'wb')
        cPickle.dump(x, f)
        f.close()
    except Exception as e:
        print "in pic", str(e)

