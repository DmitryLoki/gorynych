from gorynych.info.restui.base_resource import APIResource

__author__ = 'Boris Tsema'


class ContestResourceCollection(APIResource):
    '''
    Resource /contest
    '''
    allowedMethods = ["GET", "POST"]
    service_command = dict(POST='create_new_contest', GET='get_contests')
    name = 'contest_collection'

    def _get_args(self, args):
        if args.has_key('hq_coords'):
            args['hq_coords'] = args['hq_coords'].split(',')
        return args


class ContestResource(APIResource):
    '''
    Resource /contest/{id}
    '''
    service_command = dict(GET='get_contest', PUT='change_contest')
    name = 'contest'


class ContestRaceResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race
    '''
    service_command = dict(GET='get_contest_races',
                           POST='create_new_race_for_contest')
    name = 'contest_race_collection'


class ContestRaceResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}
    '''
    service_command = dict(GET='get_contest_race',
                           PUT='change_contest_race')
    name = 'contest_race'


class ContestParagliderResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider
    '''
    service_command = dict(POST='register_paraglider_on_contest',
                           GET='get_contest_paragliders')
    name = 'contest_paraglider_collection'


class ContestParagliderResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider/{id} or
    /contest/{id}/paraglider/{id}
    '''
    service_command = dict(PUT='change_paraglider')
    name = 'contest_paraglider_collection'


class PersonResourceCollection(APIResource):
    '''
    /person resource
    '''
    service_command = dict(GET='get_persons', POST='create_new_person')
    name = 'person_collection'


class PersonResource(APIResource):
    '''
    /person/{id} resource
    '''
    service_command = dict(GET='get_person', PUT='change_person')
    name = 'person'