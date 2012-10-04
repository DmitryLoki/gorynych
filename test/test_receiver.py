import mock
from twisted.application import service
from twisted.internet import defer
from twisted.python import log

__author__ = 'Boris Tsema'

from twisted.trial import unittest

class DomainEventStore(object):
    def save(self, event):
        return event

class TestEventStore(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_save(self):
        es = DomainEventStore()
        self.assertEqual(1, es.save(1))


class ReceiverService(service.Service):
    def __init__(self, des=DomainEventStore):
        self.des = des

    def handle_domain_event(self, devent):
        d = defer.maybeDeferred(self.des.save, devent)
        d.addCallbacks(self._choose_event_processor)
        d.addCallback(lambda ev: getattr(ev, 'process'))
        d.addErrback(log.err)

    def _choose_event_processor(self, devent):
        pass


class DomainEvent(object):

    type = "AbstractDomainEvent"

    def process(self):
        raise NotImplementedError("Process method hasn't been choosed.")


class TestReceiver(unittest.TestCase):

    def test_handle_domain_event(self):
        re = ReceiverService()
        devent = DomainEvent()
        with mock.patch.object(DomainEventStore, 'save') as ds:
            ds.return_value = devent
            with mock.patch.object(ReceiverService,
                            '_choose_event_processor') as ep:
                re.handle_domain_event(devent)
                ds.assert_called_with(devent)
                ep.assert_called_with(devent)

            ds.side_effect = Exception("Bo")
            with mock.patch.object(ReceiverService,
                            '_choose_event_processor') as ep2:
                re.handle_domain_event(devent)
                ds.assert_called_with(devent)
                self.assertFalse(ep2.called)
                errors = self.flushLoggedErrors(Exception)

    def test_choose_event_processor(self):
        re = ReceiverService()
        devent = DomainEvent()
        processed_devent = re._choose_event_processor(devent)
