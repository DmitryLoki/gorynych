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
            return dict(title=cont.title,
                        id=cont.id,
                        contest_country_code=cont.country,
                        contest_start_date=cont.start_time,
                        contest_end_date=cont.end_time)

    def read_GET(self, cont_list, request_params=None):
        if cont_list:
            result = []
            for cont in cont_list:
                result.append(dict(id=cont.id,
                                   title=cont.title,
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

    def __read(self, cont):
        '''
        @type cont: gorynych.info.domain.contest.Contest
        '''
        return dict(title=cont.title,
            id=cont.id,
            country=cont.country,
            start_time=cont.start_time,
            end_time=cont.end_time,
            coords=cont.hq_coords,
            retrieve_id=cont.retrieve_id)

    def read_GET(self, cont, request_params=None):
        if cont:
            return self.__read(cont)

    def read_PUT(self, cont, request_params=None):
        if cont:
            return self.__read(cont)


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
            return dict(type=race.type,
                        title=race.title,
                        id=race.id,
                        start_time=race.start_time,
                        end_time=race.end_time)

    def read_GET(self, race_list, request_params=None):
        result = []
        if race_list:
            for race in race_list:
                result.append(dict(id=race.id,
                                   title=race.title,
                                   start_time=race.start_time,
                                   end_time=race.end_time,
                                   type=race.type))
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
            result['optdistance'] = "%0.1f" % (r.optimum_distance/1000)
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
            result['checkpoints'] = checkpoints
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
                    contest_number=str(cont.paragliders[par_id]['contest_number']),
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
                    contest_number=str(cont.paragliders[par_id]['contest_number']),
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
                result.append(dict(id=pers.id,
                                   name=pers.name.full()))
            return result

    def read_POST(self, pers, request_params=None):
        if pers:
            return dict(name=pers.name.full(),
                        id=pers.id,
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
            trackers = []
            for t in pers.trackers:
                trackers.append([str(pers.trackers[t]), str(t)])
            response = dict(name=pers.name.full(),
                            id=pers.id,
                            country=pers.country,
                            trackers=trackers)
            return response

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
                result.append(dict(contest_number=str(key),
                                   glider=r.paragliders[key].glider,
                                   name=r.paragliders[key].name,
                                   person_id=r.paragliders[key].person_id,
                                   country=r.paragliders[key].country,
               tracker=r.paragliders[key].tracker_id if r.paragliders[key]
               .tracker_id else ''))
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
            result['checkpoints'] = checkpoints
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
                paragliders_found=result['paragliders_found'],
                parsed_tracks=result['parsed_tracks'],
                unparsed_tracks=result['unparsed_tracks'],
                tracks_without_paragliders=result['extra_tracks'],
                paragliders_without_tracks=result['without_tracks']
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
                result.append(dict(track_type=row[0],
                                   id=row[1],
                                   start_time=st,
                                   end_time=et))
            return result


class TrackerResourceCollection(APIResource):
    '''
    /tracker
    '''
    name = 'tracker_collection'
    service_command = dict(POST='create_new_tracker', GET='get_trackers')

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
            result['last_point'] = t.last_point
            return result

    def read_GET(self, rows, p=None):
        if rows:
            result = []
            for row in rows:
                try:
                    tid, name, did, dtype, lat, lon, alt, ts, bt, sp = row
                    result.append(
                        dict(device_id=did,
                             name=name,
                             device_type=dtype,
                             id=tid,
                             last_point=[lat, lon, alt, ts, bt, sp]))
                except Exception:
                    pass
            return result


class TrackerResource(APIResource):
    '''
    /tracker/{id}
    '''
    service_command = dict(GET='get_tracker', PUT='change_tracker')
    name = 'tracker'

    def read_GET(self, t, p=None):
        if t:
            return dict(id=t.id,
                        device_id=t.device_id,
                        name=t.name,
                        last_point=t.last_point)

    def read_PUT(self, t, p=None):
        return self.read_GET(t)


class TransportResourceCollection(APIResource):
    '''
    /transport
    '''
    name = 'transport_collection'
    service_command = dict(POST='create_new_transport', GET='get_transports')

    def read_GET(self, transport_list, p=None):
        if transport_list:
            result = []
            for t in transport_list:
                result.append(self.read_POST(t))
            return result

    def read_POST(self, t, p=None):
        '''
        @type t: L{gorynych.info.domain.transport.Transport}
        '''
        if t:
            result = dict()
            result['id'] = str(t.id)
            result['title'] = t.title
            result['description'] = t.description
            result['type'] = t.type
            return result


class TransportResource(APIResource):
    '''
    /transport/{id}
    '''
    name = 'transport'
    service_command = dict(GET='get_transport', PUT='change_transport')

    def __read(self, t):
        result = dict()
        result['id'] = str(t.id)
        result['title'] = t.title
        result['description'] = t.description
        result['type'] = t.type
        return result

    def read_PUT(self, t, p=None):
        if t:
            return self.__read(t)

    def read_GET(self, t, p=None):
        if t:
            return self.__read(t)


class ContestTransportCollection(APIResource):
    '''
    /contest/{id}/transport
    '''
    name = 'contest_transport_collection'
    service_command = dict(POST='add_transport_to_contest',
        GET='get_contest_transport')


    def read_GET(self, t, p=None):
        if t:
            result = []
            result.append(self.read_POST(t))
            return self.read_POST(t)

    def read_POST(self, cont, p=None):
        if cont:
            return cont.transport


class RaceTransportCollection(APIResource):
    '''
    /race/{id}/transport
    '''
    name = 'race_transport_collection'
    service_command = dict(GET='get_race',
                           PUT='change_race_transport')

    def read_GET(self, r, p=None):
        '''
        @type r: gorynych.info.domain.race.Race
        '''
        if r:
            return [dict(id=t['transport_id'],
                         title=t['title'],
                         description=t['description'],
                         type=t['type'],
                         tracker=t['tracker_id']) for t in r.transport]


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

