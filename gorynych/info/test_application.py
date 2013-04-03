# coding=utf-8
import gc

import mock

from zope.interface import implements
from twisted.trial import unittest
from twisted.internet import defer

from gorynych.info.application import ApplicationService
from gorynych.info.domain.contest import IContestRepository


class GoodContestRepository:
    implements(IContestRepository)
    store = dict()
    def save(self, obj):
        self.store[obj.id] = obj
        return obj
    def get_by_id(self, id):
        return self.store.get(id)
    def get_list(self, limit=None, offset=0):
        results = self.store.values()
        if offset >= len(results):
            return None
        else:
            results = results[offset:]
        if limit:
            return results[:limit]
        else:
            return results


class BadContestRepository:
    implements(IContestRepository)
    def save(self, obj):
        raise IndentationError("boom")


@mock.patch('gorynych.common.infrastructure.persistence.get_repository')
class ContestServiceTest(unittest.TestCase):
    def setUp(self):
        self.cs = ApplicationService(mock.Mock())
        self.cs.startService()

    def tearDown(self):
        self.cs.stopService()
        del self.cs
        gc.collect()

    def test_succes_contest_creation(self, patched):
        repository = GoodContestRepository()
        patched.return_value = repository
        d = self.cs.create_new_contest(dict(title='hoi', start_time=1,
            end_time=2, contest_place='Боливия', contest_country='RU',
            hq_coords=[12.3, 42.9]))
        cont1 = d.result
        self.assertEqual(cont1['title'], 'Hoi')
        self.assertEqual(len(cont1['id']), 36)

        cont2 = self.cs.get_contest(cont1['id']).result
        self.assertDictEqual(cont1, cont2)

        cont_list = self.cs.get_contests().result
        self.assertEqual(cont2['id'], cont_list[0]['contest_id'])

        new_cont = self.cs.change_contest(dict(id=cont1['id'],
            title='A')).result
        self.assertEqual(new_cont['title'], 'A')
        self.assertEqual(repository.get_by_id(cont1['id']).title, 'A')


    def test_bad_contest_saving(self, patched):
        patched.return_value = BadContestRepository()
        d = self.cs.create_new_contest(dict(title='hoi', start_time=3,
            end_time=5, contest_place='Боливия', contest_country='RU',
            hq_coords=[12.3, 42.9]))
        self.assertFailure(d, IndentationError)


    def test_bad_contest_creation(self, patched):
        patched.return_value = GoodContestRepository()
        d = defer.Deferred()
        d.addCallback(self.cs.create_new_contest)
        d.callback(dict(title='hoi', start_time=3, end_time=2,
            contest_place='Боливия', contest_country='RU',
            hq_coords=[12.3, 42.9]))
        self.assertFailure(d, ValueError)



if __name__ == '__main__':
    unittest.main()
