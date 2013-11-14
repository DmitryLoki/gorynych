from twisted.trial.unittest import TestCase

from gorynych.receiver.receiver import ReceiverRabbitService
from gorynych.common.infrastructure.messaging import FakeRabbitMQService


class TestReceiverRabbitService(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQService(ReceiverRabbitService)

    def test_message_transfer(self):
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)

