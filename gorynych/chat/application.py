__author__ = 'Boris Tsema'

from zope.interface import Interface, implementer
from twisted.application.service import Service

from gorynych.chat.domain.model import MessageFactory


class IChatService(Interface):
    '''
    Chat service.
    '''
    def post_message(chatroom, msg):
        '''
        Receive new message for chatroom.
        @param chatroom:
        @type chatroom: C{str}
        @param msg: dictionary with message fields
        @type msg: C{dict}
        @return: message identificator in DB.
        @rtype: C{int}
        '''

    def get_messages(chatroom, from_time, to_time):
        '''
        Return messages from service.
        @param chatroom:
        @type chatroom:
        @param from_time:
        @type from_time:
        @param to_time:
        @type to_time:
        @return:
        @rtype: C{list}
        '''


@implementer(IChatService)
class ChatApplication(Service):
    factory = MessageFactory()

    def __init__(self, repo, auth_service):
        self.repository = repo
        self.auth_service = auth_service

    def post_message(self, chatroom, msg):
        m = self.factory.create_message(msg)
        return self.repository.save(m, chatroom)

    def get_messages(self, chatroom, from_time=None, to_time=None):
        return self.repository.get_messages(chatroom, from_time, to_time)


    def get_udid_token(self, udid):
        return self.auth_service.get_udid_token(udid)