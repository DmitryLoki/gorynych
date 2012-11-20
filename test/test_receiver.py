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
    def __init__(self, des=DomainEventStore, specs=[]):
        self.des = des
        self.specifications = specs

    def handle_incoming_msg(self, msg):
        d = defer.maybeDeferred(self.des.save, msg)
        d.addCallbacks(self._choose_event_processor)
        d.addCallback(lambda ev: getattr(ev, 'process'))
        d.addErrback(log.err)

    def _build_domain_event(self, msg, klass):
        return klass(msg)

    def _choose_event_processor(self, msg):
        for specification in self.specifications:
            if specification.is_satisfied_by(msg):
                return self._build_domain_event(msg, specification.class_name)
        return self._build_domain_event(msg, DomainEvent)


class DomainEvent(object):

    type = "AbstractDomainEvent"

    def __init__(self, msg):
        self.msg = msg

    def process(self):
        raise NotImplementedError("Process method hasn't been choosed.")


class Specification(object):

    def is_satisfied_by(self, msg):
        raise NotImplementedError("Specification hasn't been implemented.")

class tr203CoordsReceivedSpecification(Specification):

    def is_satisfied_by(self, msg):
        pass

class TestReceiver(unittest.TestCase):

    def setUp(self):
        self.receiver_service = ReceiverService()
        self.receiver_service.startService()

    def tearDown(self):
        self.receiver_service.stopService()

    def test_handle_domain_event(self):
        devent = dict(name="ss")
        with mock.patch.object(DomainEventStore, 'save') as ds:
            ds.return_value = devent
            with mock.patch.object(ReceiverService,
                            '_choose_event_processor') as ep:
                self.receiver_service.handle_incoming_msg(devent)
                ds.assert_called_with(devent)
                ep.assert_called_with(devent)

            ds.side_effect = Exception("Bo")
            with mock.patch.object(ReceiverService,
                            '_choose_event_processor') as ep2:
                self.receiver_service.handle_incoming_msg(devent)
                ds.assert_called_with(devent)
                self.assertFalse(ep2.called)
                errors = self.flushLoggedErrors(Exception)

    def test_choose_event_processor(self):
        devent = dict(name='Basya')
        processed_devent = self.receiver_service._choose_event_processor(devent)
        self.assertIsInstance(processed_devent, DomainEvent)
