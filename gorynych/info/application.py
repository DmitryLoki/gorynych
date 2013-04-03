'''
Application Services for info context.
'''
import uuid

from zope.interface import Interface
from twisted.application.service import Service
from twisted.internet import defer

from gorynych.info.domain import contest
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
    return dict(title=cont.title, id=cont.id)

def read_contest_list(cont_list):
    result = []
    for cont in cont_list:
        result.append(dict(contest_id=cont.id, contest_title=cont.title,
            start_time=cont.start_time, end_time=cont.end_time))
    return result


class ApplicationService(Service):

    def __init__(self, event_publisher=None):
        self.event_publisher = event_publisher

    def startService(self):
        self.contest_factory = contest.ContestFactory(self.event_publisher)
        Service.startService(self)

    def stopService(self):
        Service.stopService(self)


    def create_new_contest(self, params, id=None):
        '''
        Create totally new contest, save it to repository and return dict
        with contest parameters.
        @param params:
        @type params:
        @return: C{Deferred} which will be fired with dictionary with contest
        parameters.
        @rtype: C{dict}
        '''
        if not id:
            id = contest.ContestID(str(uuid.uuid4()))
        cont = self.contest_factory.create_contest(id,
            params['title'],
            params['start_time'], params['end_time'],
            params['contest_place'], params['contest_country'],
            params['hq_coords'])

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
        if params:
            limit = params.get('limit', None)
            offset = params.get('offset', 0)
        else:
            limit = None
            offset = 0

        d = defer.succeed(limit)
        d.addCallback(persistence.get_repository(contest.IContestRepository)
                                                .get_list, offset)
        d.addCallback(read_contest_list)
        return d


    def get_contest(self, id):
        '''
        Return contest by id.
        @param id:
        @type id:
        @return: dictionary with contest data
        @rtype: C{Deffered}
        '''
        d = defer.succeed(id)
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
        id = params.get('id')
        if not id:
            raise ValueError("No contest id has been received.")
        del params['id']

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
            for param in params.keys():
                setattr(cont, param, params[param])
            return cont

        d = defer.succeed(id)
        d.addCallback(persistence.get_repository(contest.IContestRepository
                                ).get_by_id)
        d.addCallback(change, params)
        d.addCallback(persistence.get_repository(contest.IContestRepository)
                                        .save)
        d.addCallback(read_contest)
        return d


