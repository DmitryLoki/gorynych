'''
Processor' Context.
'''
import os
import shutil
import zipfile

import requests

from gorynych.common.domain.model import ValueObject
from gorynych import OPTS, __version__
from twisted.python import log


def get_contest_number(track):
    track = track.split('/')[-1]
    if track.endswith('.igc'):
        words = track.split('.')
        if len(words) > 2:
            return words[-2]
        if len(words) == 2:
            return str(int(words[0]))
    elif track.endswith('.kml'):
        words = track.split('.')
        return words[-2]

    pass


class TrackArchive(ValueObject):
    '''
    Download and unpack archive with race tracks.
    '''
    def __init__(self, race_id, archive_url, download_dir=None):
        if not download_dir:
            download_dir = OPTS['workdir']
        self.race_id = str(race_id)
        self.archive_url = str(archive_url)
        if not self.archive_url.endswith('zip'):
            raise ValueError("I'm waiting for zip-file link but got %s" %
                             archive_url)
        if not os.path.isdir(download_dir):
            raise ValueError("%s is not a directory" % download_dir)
        self.download_dir = download_dir

    def process_archive(self):
        '''
        Facade method.
        @return: filenames from archive
        @rtype: C{list}
        '''
        archive_file = self.download_archive()
        unpack_dir = os.path.join(self.download_dir, self.race_id)
        if os.path.isdir(unpack_dir):
            shutil.rmtree(unpack_dir)
        os.mkdir(unpack_dir)
        a_filelist = self.unpack(archive_file, unpack_dir)
        cont_numbers = self.get_race_paragliders()
        result = self.find_paragliders_tracks(a_filelist, cont_numbers)
        return result

    def download_archive(self):
        r = requests.get(self.archive_url)
        archive_path = os.path.join(self.download_dir, self.race_id + '.zip')
        with open(archive_path, 'wb') as f:
            f.write(r.content)
        return archive_path

    def unpack(self, archive_file, unpack_dir):
        namelist = []
        arc = zipfile.ZipFile(archive_file)
        for item in arc.infolist():
            # Try to solve problem with national encodings.
            # It's a mindless copy/paste from working code.
            fn = item.filename
            try:
                fnd = unicode(fn, 'utf-8', 'replace')
            except:
                fnd = fn
            fne = fnd.encode('ascii', 'replace')
            if os.sep in fne:
                path = os.path.join(unpack_dir, fne[:fne.rindex(os.sep)])
                if not os.path.exists(path):
                    os.makedirs(path)
            if fne.endswith(os.sep): continue
            f = open(os.path.join(unpack_dir, fne), 'wb')
            f.write(arc.open(fn).read())
            f.close()
            namelist.append('/'.join((unpack_dir, fne)))
        print namelist
        return namelist

    def get_race_paragliders(self):
        '''

        @return: {contest_number:person_id}
        @rtype: C{dict}
        '''
        # TODO: something wrong here...
        url = '/'.join((OPTS['apiurl'],'v' + str(__version__), 'race', self.race_id,
                        'paragliders'))
        r = requests.get(url)
        res = r.json()
        result = dict()
        for i, item in enumerate(res):
            cn = item['contest_number']
            pid = item['person_id']
            result[cn] = pid
        return result

    def find_paragliders_tracks(self, a_filelist, paragliders):
        '''
        Lookup for files wich has paragliders tracks.
        @param a_filelist: list with track filenames
        @type a_filelist: C{list}
        @param paragliders: {contest_number:person_id}
        @type paragliders: C{dict}
        @return:
        ([{person_id, trackfile, contest_number}, ...],
        [extra trackfile,],
         [person_id without tracks,]) -
         finded tracks for persons,
         extra tracks,
        paragliders without tracks.
        @rtype: C{tuple}
        '''
        tracklist = filter(lambda x :
                       x.endswith('.igc') or x.endswith('.kml'), a_filelist)
        extra_tracks = []
        tracks = []
        for idx, item in enumerate(tracklist):
            try:
                contest_number = get_contest_number(item)
            except:
                continue
            if paragliders.has_key(contest_number):
                tracks.append(dict(person_id=paragliders[contest_number],
                                   trackfile=item,
                                   contest_number=contest_number))
                del paragliders[contest_number]
            else:
                extra_tracks.append(item)
        left_paragliders = paragliders.keys()
        return tracks, extra_tracks, left_paragliders

