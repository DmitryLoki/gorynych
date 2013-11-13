from twisted.trial.unittest import TestCase

from gorynych.processor.trackservice import OnlineTrashService
from gorynych.common.infrastructure.messaging import FakeRabbitMQService


class TestReceiverRabbitService(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQService(OnlineTrashService)

    def test_message_transfer(self):
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)
