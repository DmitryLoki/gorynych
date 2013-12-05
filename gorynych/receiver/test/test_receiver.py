from twisted.trial.unittest import TestCase
from twisted.trial.unittest import SkipTest

from gorynych.receiver.receiver import ReceiverRabbitQueue
from gorynych.common.infrastructure.messaging import FakeRabbitMQObject


class TestReceiverRabbitQueue(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQObject(ReceiverRabbitQueue)
        self.sender.open('some_queue')

    def test_message_transfer(self):
        raise SkipTest(
            'read returns Deferred now; and this test is too general to bee here')
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)
