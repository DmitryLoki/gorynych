'''
Application Services for info context.
'''
import uuid

from zope.interface import Interface
from twisted.application.service import Service
from twisted.internet import defer

from gorynych.info.domain import contest, person, race
from gorynych.common.infrastructure import persistence


class TrackerService(Interface):
    '''
    Application Service which work with Tracker aggregate.
    '''

    def create_tracker(tracker_id, device_id, device_type):
        '''
        Create new tracker.
        @param tracker_id:
        @type tracker_id:
        @param device_id:
        @type device_id:
        @param device_type:
        @type device_type:
        @return: new tracker
        @rtype: Tracker
        '''

    def change_tracker_name(tracker_id, new_name):
        '''

        @param tracker_id:
        @type tracker_id:
        @param new_name:
        @type new_name:
        @return: changed tracker
        @rtype: Tracker
        '''

    def get_tracker(tracker_id):
        '''

        @param tracker_id:
        @type tracker_id:
        @return: a tracker
        @rtype: Tracker
        '''

    def get_trackers(tracker_ids):
        '''
        Get a bunch of trackers
        @param tracker_ids:
        @type tracker_ids: list
        @return: a list of trackers,
        @rtype: Tracker
        '''

    def assign_tracker_to(tracker_id, assignee_id):
        '''
        Assign a tracker with tracker_id to person or transport with
        assignee_id.
        @param tracker_id:
        @type tracker_id:
        @param assignee_id:
        @type assignee_id:
        @return:
        @rtype:
        '''

    def unassign_tracker(tracker_id):
        '''
        Unassign tracker with tracker_id from someone if tracker is assigned.
        @param tracker_id:
        @type tracker_id:
        @return:
        @rtype:
        '''


def read_contest(cont):
    if cont:
        return dict(contest_title=cont.title,
                    contest_id=cont.id,
                    contest_country_code=cont.country,
                    contest_start_date=cont.start_time,
                    contest_end_date=cont.end_time)


def read_contest_list(cont_list):
    if cont_list:
        result = []
        for cont in cont_list:
            result.append(dict(contest_id=cont.id,
                               contest_title=cont.title,
                               contest_start_time=cont.start_time,
                               contest_end_time=cont.end_time))
        return result


def read_person(pers):
    if pers:
        return dict(person_name=pers.name.full(),
                    person_id=pers.id,
                    person_country=pers.country)


def read_person_list(pers_list):
    if pers_list:
        result = []
        for pers in pers_list:
            result.append(dict(person_id=pers.id,
                               person_name=pers.name.full()))
        return result


def read_race(race):
    if race:
        return dict(race_type=race.task.type,
                    race_title=race.title,
                    race_id=race.id,
                    race_start_time=race.start_time,
                    race_end_time=race.end_time)


def read_race_list(r_list):
    result = []
    if r_list:
        for item in r_list:
            result.append(read_race(item))
        return result


def read_paraglider_list(p_list):
    pass


def read_contest_paraglider(cont, par_id):
    if cont and par_id and cont.paragliders:
        return dict(person_id=par_id,
                    contest_number=cont.paragliders[par_id]['contest_number'],
                    glider=cont.paragliders[par_id]['glider'])


def read_contest_paraglider_list(p_dicts):
    if p_dicts:
        result = []
        for person_id in p_dicts:
            result.append(dict(person_id=person_id,
                               glider=p_dicts[person_id]['glider'],
                               contest_number=str(p_dicts[person_id][
                                   'contest_number'])))
        return result


class ApplicationService(Service):
    def __init__(self, event_publisher=None):
        self.event_publisher = event_publisher

    def startService(self):
        Service.startService(self)

    def stopService(self):
        Service.stopService(self)

    ############## Contest Service part #############
    def create_new_contest(self, params):
        '''
        Create totally new contest, save it to repository and return dict
        with contest parameters.
        @param params:
        @type params:
        @return: C{Deferred} which will be fired with dictionary with contest
        parameters.
        @rtype: C{dict}
        '''
        id = contest.ContestID(str(uuid.uuid4()))
        contest_factory = contest.ContestFactory(self.event_publisher)
        cont = contest_factory.create_contest(id, params['title'],
                                              params['start_time'],
                                              params['end_time'],
                                              params['place'],
                                              params['country'],
                                              params['hq_coords'],
                                              params['timezone'])
        d = defer.succeed(cont)
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .save)
        d.addCallback(read_contest)
        return d

    def get_contests(self, params=None):
        '''
        Return a list of contests
        @param params: offset and limits can be here
        @type params: dict
        @return:
        @rtype:
        '''
        return self._get_aggregates_list(params, contest.IContestRepository,
                                         read_contest_list)

    def get_contest(self, params):
        '''
        Return contest by id.
        @param params:
        @type params: C{dict}
        @return: dictionary with contest data
        @rtype: C{Deffered}
        '''
        d = defer.succeed(params['contest_id'])
        d.addCallback(persistence.get_repository(contest.IContestRepository).
        get_by_id)
        d.addCallback(read_contest)
        return d

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
                                      change, read_contest)

    def register_paraglider_on_contest(self, params):
        d = defer.succeed(params['contest_id'])
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .get_by_id)
        d.addCallback(lambda cont: cont.register_paraglider(
            params['person_id'], params['glider'], params['contest_number']))
        d.addCallback(
            persistence.get_repository(contest.IContestRepository).save)
        d.addCallback(read_contest_paraglider, params['person_id'])
        return d

    def get_contest_paragliders(self, params):
        '''
        Return list with race paragliders.
        @param params:
        @type params:
        @return:
        @rtype:
        '''
        d = defer.succeed(params['contest_id'])
        d.addCallback(persistence.get_repository(contest.IContestRepository).
        get_by_id)
        d.addCallback(lambda cont: cont.paragliders)
        d.addCallback(read_contest_paraglider_list)
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
            allowed_changes = ['glider', 'contest_number']
            for item in allowed_changes:
                if params.has_key(item):
                    cont.change_participant_data(person_id, **params)
            return cont

        person_id = params['person_id']
        del params['person_id'] # yes, this is necessary

        d = defer.succeed(params['contest_id'])
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .get_by_id)
        d.addCallback(change)
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .save)
        d.addCallback(read_contest_paraglider, person_id)
        return d


    ############## Person Service part ##############
    def create_new_person(self, params):
        factory = person.PersonFactory(self.event_publisher)
        year, month, day = params['reg_date'].split(',')
        pers = factory.create_person(params['name'], params['surname'],
                                     params['country'], params['email'], year,
                                     month, day)
        d = defer.succeed(pers)
        d.addCallback(persistence.get_repository(person.IPersonRepository).
        save)
        d.addCallback(read_person)
        return d

    def get_person(self, params):
        d = defer.succeed(params['person_id'])
        d.addCallback(persistence.get_repository(person.IPersonRepository).
        get_by_id)
        d.addCallback(read_person)
        return d

    def get_persons(self, params=None):
        return self._get_aggregates_list(params, person.IPersonRepository,
                                         read_person_list)

    def change_person(self, params):
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
                                      change, read_person)

    ############## Race Service part ################
    def create_new_race_for_contest(self, params):
        d = defer.succeed(params['contest_id'])
        d.addCallback(persistence.get_repository(contest.IContestRepository)
        .get_by_id)
        d.addCallback(lambda cont: cont.new_race(params['race_type'],
                                                 params['checkpoints'],
                                                 params['race_title']))
        d.addCallback(persistence.get_repository(race.IRaceRepository).save)
        d.addCallback(read_race)
        return d

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

    def get_contest_race(self, params):
        '''
        Return info about race in contest and about corresponding contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''

    def change_contest_race(self, params):
        '''
        Change information about race in contest.
        @param params:
        @type params:
        @return:
        @rtype:
        '''

    ############## common methods ###################
    def _get_aggregate(self, id, repository):
        d = defer.succeed(id)
        d.addCallback(persistence.get_repository(repository).get_by_id)
        return d

    def _change_aggregate(self, params, repo_interface, change_func,
                          read_func):
        id = params.get('id')
        if not id:
            raise ValueError("Aggregate's id hasn't been received.")
        del params['id']

        d = defer.succeed(id)
        d.addCallback(persistence.get_repository(repo_interface).get_by_id)
        d.addCallback(change_func, params)
        d.addCallback(persistence.get_repository(repo_interface).save)
        d.addCallback(read_func)
        return d

    def _get_aggregates_list(self, limit_offset_params, repo_interface,
                             read_func):
        if limit_offset_params:
            limit = limit_offset_params.get('limit', None)
            offset = limit_offset_params.get('offset', 0)
        else:
            limit = None
            offset = 0

        d = defer.succeed(limit)
        d.addCallback(persistence.get_repository(repo_interface).get_list,
                      offset)
        d.addCallback(read_func)
        return d
