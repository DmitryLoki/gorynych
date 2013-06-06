# coding=utf-8
import unittest
import os
import shutil
import zipfile


from gorynych.processor import domain
from gorynych.info.domain.ids import RaceID


class TestTrackArchive(unittest.TestCase):
    def setUp(self):
        self.race_id = RaceID()

    def test_init(self):
        t = domain.TrackArchive(self.race_id, 'blabla.zip', './')
        self.assertEqual(t.race_id, str(self.race_id))
        self.assertEqual(t.archive_url, 'blabla.zip')
        self.assertEqual(t.download_dir, './')

    def test_unpack(self):
        t = domain.TrackArchive(self.race_id, 'blabla.zip', './')
        dirname = './testunpack'
        if os.path.isdir(dirname):
            shutil.rmtree(dirname)
        os.mkdir(dirname)
        namelist = t.unpack('test.zip', dirname)
        archfiles_count = len(zipfile.ZipFile('test.zip').infolist())
        unpacked_files_count = len(os.listdir(dirname))
        self.assertEqual(len(namelist), archfiles_count)
        self.assertEqual(archfiles_count, unpacked_files_count)

    def test_find_paragliders_tracks(self):
        def get_contest_number(item):
            return item.split('.')[0]
        domain.get_contest_number = get_contest_number
        flist = ['1.igc', '2.igx', '3.kml', u'a/b/s/BARISЌ.k']
        paragliders = {'1':'person_id', '8': 'pid'}
        t = domain.TrackArchive(self.race_id, 'blabla.zip', './')
        trcks, exttrcks, lftrp = t.find_paragliders_tracks(flist, paragliders)
        self.assertDictEqual(trcks[0], {'person_id': 'person_id',
            'trackfile':'1.igc', 'contest_number': '1'})
        self.assertListEqual(exttrcks, ['3.kml'])
        self.assertListEqual(lftrp, ['pid'])


class TestGetContestNumbers(unittest.TestCase):
    def test_world(self):
        track = '0032.igc'
        self.assertEqual(domain.get_contest_number(track), '32')

    def test_kml(self):
        track = 'BARIŞ TURA.20120705-162829.[CIVLID].11.kml'
        self.assertEqual(domain.get_contest_number(track), '11')

    def test_paramania(self):
        track = 'Alex Tarakanov.20120429-152742.0.52.igc'
        self.assertEqual(domain.get_contest_number(track), '52')


if __name__ == '__main__':
    unittest.main()
