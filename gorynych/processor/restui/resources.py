from gorynych.info.restui.base_resource import APIResource


# TODO: do this without subclassing APIResource?
class TracksResource(APIResource):
    '''
    /group/{id}/tracks
    Return track data and state.
    '''
    service_command = dict(GET='get_track_data')
    isLeaf = True

    def read_GET(self, trs, params=None):
        if trs:
            return trs
