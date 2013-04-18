from gorynych.info.restui.base_resource import APIResource

__author__ = 'Boris Tsema'


class ContestResourceCollection(APIResource):
    '''
    Resource /contest
    '''
    service_command = dict(POST='create_new_contest',
                           GET='get_contests')
    name = 'contest_collection'

    def _get_args(self, args):
        if args.has_key('hq_coords'):
            args['hq_coords'] = args['hq_coords'].split(',')
        return args

    def read_POST(self, cont, request_params=None):
        if cont:
            return dict(contest_title=cont.title,
                        contest_id=cont.id,
                        contest_country_code=cont.country,
                        contest_start_date=cont.start_time,
                        contest_end_date=cont.end_time)

    def read_GET(self, cont_list, request_params=None):
        if cont_list:
            result = []
            for cont in cont_list:
                result.append(dict(contest_id=cont.id,
                                   contest_title=cont.title,
                                   contest_start_time=cont.start_time,
                                   contest_end_time=cont.end_time))
            return result


class ContestResource(APIResource):
    '''
    Resource /contest/{id}
    '''
    service_command = dict(GET='get_contest',
                           PUT='change_contest')
    name = 'contest'

    def read_GET(self, cont, request_params=None):
        if cont:
            return dict(contest_title=cont.title,
                        contest_id=cont.id,
                        contest_country_code=cont.country,
                        contest_start_date=cont.start_time,
                        contest_end_date=cont.end_time)

    def read_PUT(self, cont, request_params=None):
        if cont:
            return dict(contest_title=cont.title,
                        contest_id=cont.id,
                        contest_country_code=cont.country,
                        contest_start_date=cont.start_time,
                        contest_end_date=cont.end_time)


class ContestRaceResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race
    '''
    service_command = dict(GET='get_contest_races',
                           POST='create_new_race_for_contest')
    name = 'contest_race_collection'

    def read_POST(self, race, request_params=None):
        if race:
            return dict(race_type=race.task.type,
                        race_title=race.title,
                        race_id=race.id,
                        race_start_time=race.start_time,
                        race_end_time=race.end_time)

    def read_GET(self, race, request_params=None):
        return self.read_POST(race)


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

    def read_POST(self, cont, request_params):
        par_id = request_params.get('person_id')
        if cont and par_id and cont.paragliders:
            return dict(person_id=par_id,
                    contest_number=cont.paragliders[par_id]['contest_number'],
                    glider=cont.paragliders[par_id]['glider'])

    def read_GET(self, p_dicts, request_params=None):
        if p_dicts:
            result = []
            for person_id in p_dicts:
                result.append(dict(person_id=person_id,
                                   glider=p_dicts[person_id]['glider'],
                                   contest_number=str(p_dicts[person_id][
                                       'contest_number'])))
            return result


class ContestParagliderResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider/{id} or
    /contest/{id}/paraglider/{id}
    '''
    service_command = dict(PUT='change_paraglider')
    name = 'contest_paraglider_collection'

    def read_PUT(self, cont, request_params):
        print "REQUEST PARAMS ", request_params
        par_id = request_params.get('person_id')
        if cont and par_id and cont.paragliders:
            return dict(person_id=par_id,
                    contest_number=cont.paragliders[par_id]['contest_number'],
                    glider=cont.paragliders[par_id]['glider'])


class PersonResourceCollection(APIResource):
    '''
    /person resource
    '''
    service_command = dict(GET='get_persons',
                           POST='create_new_person')
    name = 'person_collection'

    def read_GET(self, pers_list, request_params=None):
        if pers_list:
            result = []
            for pers in pers_list:
                result.append(dict(person_id=pers.id,
                                   person_name=pers.name.full()))
            return result

    def read_POST(self, pers, request_params=None):
        if pers:
            return dict(person_name=pers.name.full(),
                        person_id=pers.id,
                        person_country=pers.country)


class PersonResource(APIResource):
    '''
    /person/{id} resource
    '''
    service_command = dict(GET='get_person',
                           PUT='change_person')
    name = 'person'

    def read_PUT(self, pers, request_params=None):
        if pers:
            return dict(person_name=pers.name.full(),
                        person_id=pers.id,
                        person_country=pers.country)

    def read_GET(self, pers, request_params=None):
        return self.read_PUT(pers)
