__author__ = 'Boris Tsema'
import cPickle

class TrackRepository(object):
    def persist(self, data):
        f = open('track_repo', 'wb')
        cPickle.dump(data, f, -1)
        f.close()
