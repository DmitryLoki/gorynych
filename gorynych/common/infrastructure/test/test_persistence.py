import unittest

from zope.interface.declarations import implements

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


if __name__ == '__main__':
    unittest.main()
