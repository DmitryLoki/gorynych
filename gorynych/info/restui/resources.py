import simplejson as json
import pytz
from datetime import datetime
from gorynych.info.restui.base_resource import APIResource
from gorynych.common.domain import types

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

    def _get_args(self, args):
        if args.has_key('checkpoints'):
            args['checkpoints'] = json.loads(args['checkpoints'])['features']
            for i, item in enumerate(args['checkpoints']):
                args['checkpoints'][i] = types.checkpoint_from_geojson(item)
        return args

    def read_POST(self, race, request_params=None):
        if race:
            return dict(race_type=race.type,
                        race_title=race.title,
                        race_id=race.id,
                        race_start_time=race.start_time,
                        race_end_time=race.end_time)

    def read_GET(self, race_list, request_params=None):
        result = []
        if race_list:
            for race in race_list:
                result.append(dict(race_id=race.id,
                                   race_title=race.title,
                                   race_start_time=race.start_time,
                                   race_end_time=race.end_time,
                                   race_type=race.type))
        return result


class ContestRaceResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}
    '''
    service_command = dict(GET='get_contest_race',
                           PUT='change_contest_race')
    name = 'contest_race'

    def read_GET(self, (cont, r), request_params=None):
        if cont and r:
            result = self.read_PUT(r)
            result['contest_title'] = cont.title
            result['country'] = pytz.country_names[cont.country]
            result['place'] = cont.place
            result['timeoffset'] = datetime.fromtimestamp(result[
                'start_time'],
                pytz.timezone(cont.timezone)).strftime('%z')
            return result

    def read_PUT(self, r, request_params=None):
        if r:
            result = dict()
            result['race_title'] = r.title
            result['race_type'] = r.type
            result['start_time'] = r.start_time
            result['end_time'] = r.end_time
            result['bearing'] = r.bearing
            checkpoints = {'type': 'FeatureCollection', 'features': []}
            for ch in r.checkpoints:
                checkpoints['features'].append(ch.__geo_interface__)
            result['checkpoints'] = json.dumps(checkpoints)
            return result


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


class RaceParagliderResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider,
    /race/{id}/paragliders
    '''
    name = 'race_paraglider_collection'
    service_command = dict(GET='get_race')

    def read_GET(self, r, request_params=None):
        if r:
            result = []
            for key in r.paragliders:
                result.append(dict(contest_number=key,
                                   glider=r.paragliders[key].glider,
                                   name=r.paragliders[key].name,
                                   person_id=r.paragliders[key].person_id,
                                   country=r.paragliders[key].country))
            return result


class RaceResource(APIResource):
    '''
    /race/{id} resource
    '''
    name = 'race'
    service_command = dict(GET='get_race')

    def read_GET(self, r, request_params=None):
        if r:
            result = dict()
            result['race_title'] = r.title
            result['race_type'] = r.type
            result['start_time'] = r.start_time
            result['end_time'] = r.end_time
            result['bearing'] = r.bearing
            checkpoints = {'type': 'FeatureCollection', 'features': []}
            for ch in r.checkpoints:
                checkpoints['features'].append(ch.__geo_interface__)
            result['checkpoints'] = json.dumps(checkpoints)
            return result


class Placeholder(APIResource):
    '''
    Resource which just a placeholder for children resources.
    '''
    pass


class TrackArchiveResource(APIResource):
    '''
    contest/{id}/race/{id}/trackarchive
    '''
    name = 'track_archive'
    templates = dict(GET='track_archive_GET', POST='track_archive_POST')
    service_command = dict(POST='add_track_archive', GET='get_race')

    def read_POST(self, result, p=None):
        if result:
            return dict(result=str(result))

    def read_GET(self, r, p=None):
        if r:
            result = dict()
            keys = ['paragliders_found', 'parsed_tracks', 'unparsed_tracks',
                'extra_tracks', 'without_tracks']
            ta = r.track_archive
            status = ta.state
            for key in keys:
                if ta.progress.has_key(key):
                    result[key] = json.dumps(list(ta.progress[key]))
                else:
                    result[key] = json.dumps([])
            return dict(status=status,
                found_contest_numbers=result['paragliders_found'],
                parsed_contest_numbers=result['parsed_tracks'],
                unparsed_tracks=result['unparsed_tracks'],
                extra_tracks=result['extra_tracks'],
                without_tracks=result['without_tracks']
            )


class RaceTracksResource(APIResource):
    '''
    /race/{id}/tracks,
    /contest/{id}/race/{id}/tracks
    Return list with tracks information.
    '''
    name = 'race_tracks'
    service_command = dict(GET='get_race_tracks')
    def read_GET(self, rows, params=None):
        if rows:
            result = []
            for row in rows:
                if row[2]:
                    st = int(row[2])
                else:
                    st = 'null'
                if row[3]:
                    et = int(row[3])
                else:
                    et = 'null'
                result.append(dict(type=row[0], track_id=row[1],
                    start_time=st, end_time=et))
            return result


class TrackerCollection(APIResource):
    '''
    /tracker
    '''
    name = 'tracker_collection'
    service_command = dict(POST='create_new_tracker')

    def read_POST(self, t, p=None):
        '''
        @type t: L{gorynych.info.domain.tracker.Tracker}
        '''
        if t:
            result = dict()
            result['device_id'] = t.device_id
            result['name'] = t.name
            result['device_type'] = t.device_type
            result['id'] = t.id
            return result




# TODO: this resource should be in processor package.
class TracksResource(APIResource):
    '''
    /race/{id}/tracks
    Return track data and state.
    '''
    service_command = dict(GET='get_track_data')

    def read_GET(self, trs, params=None):
        if trs:
            return json.dumps(trs)

