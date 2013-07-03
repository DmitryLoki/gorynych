'''
Application Services for info context.
'''
import cPickle
import simplejson as json

from twisted.internet import defer, task
from twisted.python import log

from gorynych.info.domain import contest, person, race, tracker
from gorynych.common.infrastructure import persistence
from gorynych.common.domain.types import checkpoint_from_geojson
from gorynych.common.domain.events import ContestRaceCreated
from gorynych.common.application import EventPollingService, DBPoolService
from gorynych.info.domain import interfaces
from gorynych.receiver.receiver import RabbitMQService


class BaseApplicationService(DBPoolService):
    def _get_aggregate(self, id, repository):
        d = defer.succeed(id)
        d.addCallback(persistence.get_repository(repository).get_by_id)
        return d

    def _change_aggregate(self, params, repo_interface, change_func):
        id = params.get('id')
        if not id:
            raise ValueError("Aggregate's id hasn't been received.")
        del params['id']

        d = self._get_aggregate(id, repo_interface)
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
        d.addCallback(persistence.get_repository(contest.IContestRepository)
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
        return self._get_aggregates_list(params, contest.IContestRepository)

    def get_contest(self, params):
        '''
        Return contest by id.
        @param params:
        @type params: C{dict}
        @return: Contest wrapped by Deferred.
        @rtype: C{Deffered}
        '''
        return self._get_aggregate(params['contest_id'],
                                contest.IContestRepository)

    def change_contest(self, params):
        '''
        Change contest information.
        @param params:
        @type params:
        @return:
        @rtype:
        '''

        def change(cont, params):
            '''
            Do actual changes in contest.
            @param cont:
            @type cont:
            @param params:
            @type params:
            @return:
            @rtype:
            '''
            if params.get('start_time') and params.get('end_time'):
                cont.change_times(params['start_time'], params['end_time'])
                del params['start_time']
                del params['end_time']

            for param in params.keys():
                setattr(cont, param, params[param])
            return cont

        if params.has_key('contest_id'):
            params['id'] = params['contest_id']
            del params['contest_id']
        return self._change_aggregate(params, contest.IContestRepository,
                                      change)

    def register_paraglider_on_contest(self, params):
        '''

        @param params:
        @type params:
        @return: Contest with registered paraglider wrapped in Deferred.
        @rtype: C{Contest}
        '''
        d = self._get_aggregate(params['contest_id'],
                                contest.IContestRepository)
        d.addCallback(lambda cont: cont.register_paraglider(
            person.PersonID.fromstring(params['person_id']), params['glider'],
            params['contest_number']))
        d.addCallback(
            persistence.get_repository(contest.IContestRepository).save)
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
                                contest.IContestRepository)
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

        def change(cont):
            if params.has_key('glider'):
                cont.change_participant_data(params['person_id'],
                                             glider=params['glider'])
            if params.has_key('contest_number'):
                cont.change_participant_data(params['person_id'],
                                     contest_number=params['contest_number'])
            return cont

        d = self._get_aggregate(params['contest_id'],
                                contest.IContestRepository)
        d.addCallback(change)
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .save)
        return d


    ############## Person Service part ##############
    def create_new_person(self, params):
        factory = person.PersonFactory()
        regdate = params.get('reg_date')
        if regdate:
            try:
                year, month, day = regdate.split(',')
            except ValueError:
                raise ValueError("Wrong regdate has been passed on pilot creation: %s" % regdate)
        else:
            year, month, day = None, None, None
        pers = factory.create_person(params['name'], params['surname'],
                                     params['country'], params['email'], year,
                                     month, day)
        d = defer.succeed(pers)
        d.addCallback(persistence.get_repository(person.IPersonRepository).
        save)
        return d

    def get_person(self, params):
        return self._get_aggregate(params['person_id'],
                                   person.IPersonRepository)

    def get_persons(self, params=None):
        return self._get_aggregates_list(params, person.IPersonRepository)

    def change_person(self, params):
        # TODO: create changing services instead of functions in application
        #  layer.
        def change(pers, params):
            new_name = dict()
            if params.get('name'):
                new_name['name'] = params['name']
            if params.get('surname'):
                new_name['surname'] = params['surname']
            pers.name = new_name
            if params.get('country'):
                pers.country = params['country']
            return pers

        if params.has_key('person_id'):
            params['id'] = params['person_id']
            del params['person_id']
        return self._change_aggregate(params, person.IPersonRepository,
                                      change)

    ############## Race Service part ################
    def get_race(self, params):
        return self._get_aggregate(params['race_id'], race.IRaceRepository)

    @defer.inlineCallbacks
    def create_new_race_for_contest(self, params):
        cont = yield self._get_aggregate(params['contest_id'],
                                contest.IContestRepository)
        paragliders = cont.paragliders
        plist = []
        # TODO: make it thinner.
        for key in paragliders:
            pers = yield self._get_aggregate(key, person.IPersonRepository)
            plist.append(contest.Paraglider(key, pers.name, pers.country,
                         paragliders[key]['glider'],
                         paragliders[key]['contest_number'],
                         pers.trackers.get(params['contest_id'])))

        factory = race.RaceFactory()
        r = factory.create_race(params['title'], params['race_type'],
                                   cont.timezone, plist,
                                   params['checkpoints'],
                                   bearing=params.get('bearing'),
                                timelimits=(cont.start_time, cont.end_time))
        # TODO: do it transactionally.
        d = persistence.get_repository(race.IRaceRepository).save(r)
        d.addCallback(lambda _:persistence.event_store().persist(ContestRaceCreated(
            cont.id, r.id)))
        yield d
        defer.returnValue(r)

    def get_contest_races(self, params):
        '''
        Return list of races for contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        d = self._get_aggregate(params['contest_id'],
                                contest.IContestRepository)
        d.addCallback(lambda cont: [self._get_aggregate(id,
                             race.IRaceRepository) for id in cont.race_ids])
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
                                      contest.IContestRepository)
        defer.returnValue((c, r))

    def change_contest_race(self, params):
        '''
        Change information about race in contest.
        @param params:
        @type params:
        @return: Race
        @rtype:
        '''
        def change(r):
            if params.has_key('checkpoints'):
                # TODO: make in thinner
                if isinstance(params['checkpoints'], str):
                    try:
                        ch_list = json.loads(params['checkpoints'])['features']
                    except Exception as e:
                        raise ValueError("Problems with checkpoint reading: %r .Got %s, %r" % (e, type(params['checkpoints']), params['checkpoints']))
                elif isinstance(params['checkpoints'], dict):
                    ch_list = params['checkpoints']['features']
                else:
                    raise ValueError("Problems with checkpoint reading: got %s, %r" % (type(params['checkpoints']), params['checkpoints']))
                checkpoints = []
                for ch in ch_list:
                    checkpoints.append(checkpoint_from_geojson(ch))
                r.checkpoints = checkpoints
            if params.has_key('race_title'):
                r.title = params['race_title']
            if params.has_key('bearing'):
                r.bearing = params['bearing']
            return r

        d = self.get_race(params)
        d.addCallback(change)
        d.addCallback(persistence.get_repository(race.IRaceRepository).save)
        return d

    def add_track_archive(self, params):
        d = self.get_race(params)
        d.addCallback(lambda r: r.add_track_archive(params['url']))
        return d

    ############## Race Track's work ##################
    def get_race_tracks(self, params):
        race_id = params['race_id']
        ttype = params.get('type')
        def filtr(rows):
            if not ttype:
                return rows
            return filter(lambda row:row[0] == ttype, rows)
        d = self.pool.runQuery(persistence.select('tracks', 'track'),
            (race_id,))
        d.addCallback(filtr)
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
        return self._get_aggregates_list(params, interfaces.ITrackerRepository)

    def get_tracker(self, params):
        return self._get_aggregate(params['tracker_id'],
            interfaces.ITrackerRepository)

    def change_tracker(self, params):
        if params.has_key('tracker_id'):
           params['id'] = params['tracker_id']
           del params['tracker_id']
        return self._change_aggregate(params, interfaces.ITrackerRepository,
            tracker.change_tracker)


class LastPointApplication(RabbitMQService):
    def __init__(self, pool, **kw):
        RabbitMQService.__init__(self, **kw)
        self.pool = pool

    def when_started(self):
        d = defer.Deferred()
        d.addCallback(self.open)
        d.addCallback(lambda x: task.LoopingCall(self.read, x))
        d.addCallback(lambda lc: lc.start(0.00))
        d.callback('last_point')
        return d

    def handle_payload(self, queue_name, channel, method_frame, header_frame,
            body):
        data = cPickle.loads(body)
        if not data.has_key('ts'):
            # ts key MUST be in a data.
            return
        log.msg(data)
        return self.pool.runOperation(persistence.update('last_point',
            'tracker'), (data['lat'], data['lon'], data['alt'], data['ts'],
        data['imei']))

