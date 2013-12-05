from twisted.trial.unittest import TestCase
from twisted.trial.unittest import SkipTest

from gorynych.processor.trackservice import OnlineTrashService
from gorynych.common.infrastructure.messaging import FakeRabbitMQObject, RabbitMQObject


class TestTrackService(TestCase):

    def setUp(self):
        self.sender = FakeRabbitMQObject(RabbitMQObject)
        self.sender.open('some_queue')

    def test_message_transfer(self):
        raise SkipTest(
            'read returns Deferred now; and this test is too general to bee here')
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)

