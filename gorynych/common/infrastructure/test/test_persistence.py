import unittest

from zope.interface.declarations import implements
import numpy as np

from gorynych.common.infrastructure import persistence
from gorynych.info.domain.interfaces import IPersonRepository


class RepositoryClass(object):
    implements(IPersonRepository)
    def get_by_id(self, id):
        pass
    def save(self, smth):
        pass


class RepositoryRegistryRegisterTest(unittest.TestCase):

    def test_register_repository(self):
        repo_instance = RepositoryClass()
        persistence.register_repository(IPersonRepository, repo_instance)

        self.assertTrue('IPersonRepository' in
                        persistence.global_repository_registry.keys())
        self.assertTrue(repo_instance in
                        persistence.global_repository_registry.values())


    def test_access_repo(self):
        self.test_register_repository()

        person_repository = persistence.get_repository(IPersonRepository)
        self.assertIsNotNone(person_repository)
        self.assertTrue(IPersonRepository.providedBy(person_repository))


class TestNpAsText(unittest.TestCase):

    def setUp(self):
        self.dtype = [('id', 'i4'),
                        ('timestamp', 'i4'),
                        ('lat', 'f8'),
                        ('lon', 'f8'),
                        ('alt', 'i2'),
                        ('g_speed', 'f4'),
                        ('v_speed', 'f4'),
                        ('distance', 'i4')]

    def test_float(self):
        a = np.ones(1, dtype=self.dtype)
        a['lat'], a['lon'], a['g_speed'], a['v_speed'] = 1/3., 1/3., 1/3., \
            1/3.
        b = persistence.np_as_text(a).read()
        c = b.split('\t')
        for i in (c[2], c[3], c[5], c[6]):
            self.assertEqual(i[:8], str(1/3.)[:8])


if __name__ == '__main__':
    unittest.main()
