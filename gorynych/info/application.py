# -*- coding: utf-8 -*-
'''
Application Services for info context.
'''
import cPickle

from twisted.internet import defer, task
from twisted.python import log

from gorynych.info.domain import contest, person, race, tracker, transport, interfaces
from gorynych.common.infrastructure import persistence
from gorynych.common.domain.events import ContestRaceCreated
from gorynych.common.domain.service import SinglePollerService
from gorynych.common.application import DBPoolService


class BaseApplicationService(DBPoolService):

    def _get_aggregate(self, id, repository):
        d = defer.succeed(id)
        d.addCallback(persistence.get_repository(repository).get_by_id)
        return d

    def _change_aggregate(self, params, repo_interface, change_func):
        aggregate_type = repo_interface.getName()[1:-10].lower()
        id_ = params.get(aggregate_type + '_id')
        if not id_:
            raise ValueError("Aggregate's id hasn't been received.")
        if params.get('id'):
            del params['id']

        d = self._get_aggregate(id_, repo_interface)
        d.addCallback(change_func, params)
        d.addCallback(persistence.get_repository(repo_interface).save)
        return d

    def _get_aggregates_list(self, limit_offset_params, repo_interface):
        if limit_offset_params:
            limit = limit_offset_params.get('limit', None)
            offset = limit_offset_params.get('offset', 0)
        else:
            limit = None
            offset = 0

        d = defer.succeed(limit)
        d.addCallback(persistence.get_repository(repo_interface).get_list,
            offset)
        return d


class ApplicationService(BaseApplicationService):

    ############## Contest Service part #############
    def create_new_contest(self, params):
        '''
        Create totally new contest and save it to repository.
        @param params:
        @type params:
        @return: C{Deferred} which will be fired with L{Contest} aggregate.
        @rtype: L{Contest}
        '''
        id = contest.ContestID()
        contest_factory = contest.ContestFactory()
        cont = contest_factory.create_contest(params['title'],
                                              params['start_time'],
                                              params['end_time'],
                                              params['place'],
                                              params['country'],
                                              params['hq_coords'],
                                              params['timezone'],
                                              id)
        d = defer.succeed(cont)
        d.addCallback(persistence.get_repository(interfaces.IContestRepository)
        .save)
        return d

    def get_contests(self, params=None):
        '''
        Return a list of contests
        @param params: offset and limits can be here
        @type params: dict
        @return:
        @rtype:
        '''
        return self._get_aggregates_list(params, interfaces.IContestRepository)

    def get_contest(self, params):
        '''
        Return contest by id.
        @param params:
        @type params: C{dict}
        @return: Contest wrapped by Deferred.
        @rtype: C{Deffered}
        '''
        return self._get_aggregate(params['contest_id'],
                                interfaces.IContestRepository)

    def change_contest(self, params):
        '''
        Change contest information.
        @param params:
        @type params:
        @return:
        @rtype:
        '''

        return self._change_aggregate(params, interfaces.IContestRepository,
                                      contest.change)

    def register_paraglider_on_contest(self, params):
        '''

        @param params:
        @type params:
        @return: Contest with registered paraglider wrapped in Deferred.
        @rtype: C{Contest}
        '''
        d = self._get_aggregate(params['contest_id'],
                                interfaces.IContestRepository)
        d.addCallback(lambda cont: cont.register_paraglider(
            person.PersonID.fromstring(params['person_id']), params['glider'],
            params['contest_number']))
        d.addCallback(
            persistence.get_repository(interfaces.IContestRepository).save)
        return d

    def add_transport_to_contest(self, params):
        d = self.get_contest(params)
        d.addCallback(lambda cont: cont.add_transport(params['transport_id']))
        d.addCallback(
            persistence.get_repository(interfaces.IContestRepository).save)
        return d

    def get_contest_transport(self, params):
        d = self.get_contest(params)
        return d

    def get_contest_paragliders(self, params):
        '''
        Return list with race paragliders.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        d = self._get_aggregate(params['contest_id'],
                                interfaces.IContestRepository)
        d.addCallback(lambda cont: cont.paragliders)
        return d

    def change_paraglider(self, params):
        '''
        Change paraglider information either for race or contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        d = self._get_aggregate(params['contest_id'],
                                interfaces.IContestRepository)
        d.addCallback(contest.change_participant, params)
        d.addCallback(persistence.get_repository(interfaces.IContestRepository)
                      .save)
        return d


    ############## Person Service part ##############
    def create_new_person(self, params):
        factory = person.PersonFactory()
        pers = factory.create_person(params['name'], params['surname'],
                                     params['country'], params['email'])
        d = defer.succeed(pers)
        d.addCallback(persistence.get_repository(interfaces.IPersonRepository).
        save)
        return d

    def get_person(self, params):
        return self._get_aggregate(params['person_id'],
                                   interfaces.IPersonRepository)

    def get_persons(self, params=None):
        return self._get_aggregates_list(params, interfaces.IPersonRepository)

    def change_person(self, params):
        return self._change_aggregate(params, interfaces.IPersonRepository,
                                      person.change_person)

    ############## Race Service part ################
    def get_race(self, params):
        return self._get_aggregate(params['race_id'], interfaces.IRaceRepository)

    @defer.inlineCallbacks
    def create_new_race_for_contest(self, params):
        cont = yield self._get_aggregate(params['contest_id'],
                                         interfaces.IContestRepository)
        person_list = []
        # TODO: make it thinner.
        for key in cont.paragliders:
            # TODO: do less db queries for transport.
            pers = yield self._get_aggregate(key, interfaces.IPersonRepository)
            person_list.append(pers)

        # TODO: do in domain model style. Think before.
        # [(type, title, desc, tracker_id, transport_id),]
        transport_list = yield self.pool.runQuery(
            persistence.select('transport_for_contest', 'transport'),
                              (str(cont.id),))

        new_race = race.create_race_for_contest(cont,
                                           person_list,
                                           transport_list,
                                           params)
        # TODO: do it transactionally.
        d = persistence.get_repository(interfaces.IRaceRepository).save(new_race)
        d.addCallback(lambda _: persistence.event_store().persist(ContestRaceCreated(
            cont.id, new_race.id)))
        yield d
        defer.returnValue(new_race)

    def get_contest_races(self, params):
        '''
        Return list of races for contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        d = self._get_aggregate(params['contest_id'],
                                interfaces.IContestRepository)
        d.addCallback(lambda cont: [self._get_aggregate(id,
                             interfaces.IRaceRepository) for id in cont.race_ids])
        d.addCallback(defer.gatherResults, consumeErrors=True)
        return d

    @defer.inlineCallbacks
    def get_contest_race(self, params):
        '''
        Return info about race in contest and about corresponding contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        r = yield self.get_race(params)
        c = yield self._get_aggregate(params['contest_id'],
                                      interfaces.IContestRepository)
        defer.returnValue((c, r))

    def change_contest_race(self, params):
        '''
        Change information about race in contest.
        @param params:
        @type params:
        @return: Race
        @rtype:
        '''
        d = self.get_race(params)
        d.addCallback(race.change_race, params)
        d.addCallback(persistence.get_repository(interfaces.IRaceRepository).save)
        return d

    def add_track_archive(self, params):
        d = self.get_race(params)
        d.addCallback(lambda r: r.add_track_archive(params['url']))
        return d

    def change_race_transport(self, params):
        return self._change_aggregate(params, interfaces.IRaceRepository,
            race.change_race_transport)


    ############## Race Track's work ##################
    def get_race_tracks(self, params):
        group_id = params['race_id']
        ttype = params.get('type')
        if ttype and ttype == 'online':
            group_id = group_id + '_online'
        # def filtr(rows):
        #     if not ttype:
        #         return rows
        #     return filter(lambda row:row[0] == ttype, rows)
        d = self.pool.runQuery(persistence.select('tracks', 'track'),
            (group_id,))
        # d.addCallback(filtr)
        return d

    ############## Tracker aggregate part ###################
    def create_new_tracker(self, params):
        from gorynych.info.domain.tracker import TrackerFactory
        factory = TrackerFactory()
        trcker = factory.create_tracker(device_id=params['device_id'],
            device_type=params['device_type'], name=params.get('name'))
        d = defer.succeed(trcker)
        d.addCallback(persistence.get_repository(
            interfaces.ITrackerRepository).save)
        return d

    def get_trackers(self, params=None):
        return self.pool.runQuery(persistence.select('trackers', 'tracker'))

    def get_tracker(self, params):
        return self._get_aggregate(params['tracker_id'],
            interfaces.ITrackerRepository)

    def change_tracker(self, params):
        return self._change_aggregate(params, interfaces.ITrackerRepository,
            tracker.change_tracker)

    ############## Transport aggregate part ################
    def create_new_transport(self, params):
        from gorynych.info.domain.transport import TransportFactory
        factory = TransportFactory()
        trns = factory.create_transport(params['type'], params['title'],
            params.get('description'))
        d = defer.succeed(trns)
        d.addCallback(persistence.get_repository(
            interfaces.ITransportRepository).save)
        return d

    def get_transports(self, params=None):
        return self._get_aggregates_list(
            params, interfaces.ITransportRepository)

    def get_transport(self, params):
        return self._get_aggregate(params['transport_id'],
            interfaces.ITransportRepository)

    def change_transport(self, params):
        return self._change_aggregate(params, interfaces.ITransportRepository,
            transport.change_transport)


class LastPointApplication(SinglePollerService):
    def __init__(self, pool, connection, **kw):
        poll_interval = kw.get('interval', 0.0)
        SinglePollerService.__init__(self, connection, poll_interval, queue_name='last_point')
        self.pool = pool
        # imei:ts
        self.points = dict()

    def handle_payload(self, queue_name, channel, method_frame, header_frame,
            body):
        data = cPickle.loads(body)
        if not data.has_key('ts'):
            # ts key MUST be in a data.
            return
        if self.points.get(data['imei']) < data['ts']:
            self.points[data['imei']] = data['ts']
            return self.pool.runOperation(persistence.update('last_point',
                'tracker'), (data['lat'], data['lon'], data['alt'], data['ts'],
            data.get('battery'), data['h_speed'], data['imei']))
