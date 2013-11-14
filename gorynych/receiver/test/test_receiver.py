from twisted.trial.unittest import TestCase

from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService
from gorynych.common.infrastructure.messaging import FakeRabbitMQService


class TestReceiverRabbitService(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQService(ReceiverRabbitService)

    def test_message_transfer(self):
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)


class TestReceiverService(TestCase):
    def test_start_service(self):
        from gorynych.receiver.parsers import App13Parser
        re = ReceiverService(1, 2, 'app13')
        re.startService()
        self.assertIsInstance(re.parsers['app13'], App13Parser)

    def test_start_unknown_parser(self):
        re = ReceiverService(1, 2, 'unknown')
        self.assertRaises(SystemExit, re.startService)