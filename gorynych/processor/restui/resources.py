import simplejson as json

from gorynych.info.restui.base_resource import APIResource


class TracksResource(APIResource):
    '''
    /group/{id}/tracks
    Return track data and state.
    '''
    service_command = dict(GET='get_track_data')
    isLeaf = True

    def read_GET(self, trs, params=None):
        if trs:
            return json.dumps(trs)


class CompleteTracksResource(APIResource):
    """
    /track/group/{id}/complete/pilots={id1},{id2},{id3}...
    """
    service_command = dict(GET='get_complete_tracks')
    isLeaf = True

    def read_GET(self, data, params=None):
        if data:
            return json.dumps(data)
