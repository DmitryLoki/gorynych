from twisted.trial import unittest
from zope.interface.verify import verifyClass

from gorynych.eventstore.interfaces import IEventStore
from gorynych.eventstore.eventstore import EventStore

class EventStoreTest(unittest.TestCase):
    def test_validate_class(self):
        verifyClass(IEventStore, EventStore)


if __name__ == '__main__':
    unittest.main()
