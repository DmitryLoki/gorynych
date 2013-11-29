from twisted.trial.unittest import TestCase

from gorynych.receiver.receiver import ReceiverRabbitQueue
from gorynych.common.infrastructure.messaging import FakeRabbitMQObject


class TestReceiverRabbitQueue(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQObject(ReceiverRabbitQueue)
        self.sender.open('some_queue')

    def test_message_transfer(self):
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)

