import simplejson as json
from twisted.python import log
from zope.interface import implementer
from twisted.web import resource, server
from twisted.web.http import stringToDatetime

from gorynych.common.exceptions import AuthenticationError


@implementer(resource.IResource)
class WebChat(resource.Resource):
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service

    def getChild(self, path, request):
        if path == 'chatroom':
            if len(request.postpath) > 0 and request.postpath[0]:
                chroom = request.postpath[0]
                return ChatResource(self.service, chroom)
        elif path == 'appinit':
            if len(request.postpath) > 0 and request.postpath[0]:
                udid = request.postpath[0]
                return AuthenticationResource(udid, self.service)
        elif path == 'handshake':
            return HandshakeResource(self.service)
        elif path == 'chatapi':
            return ChatAPI(self.service)
        elif path == 'reports':
            if len(request.postpath) == 0 or not request.postpath[0]:
                return ChatroomListResource(self.service)
            elif request.postpath[0]:
                return ReportResource(self.service, request.postpath[0])
        return self


def get_message_from_request(request):
    '''
    Read message from request object.
    @param request:
    @type request:
    @return: {from_, to, sender, body}
    @rtype: C{dict}
    '''
    args = request.args
    # If args[key] list has only one value make args[key] just a value
    # not a list.
    for key in args:
        if len(args[key]) == 1:
            args[key] = args[key][0]
    assert len(args) > 3, "Not enouqh parameters in request."
    return args


class ChatroomListResource(resource.Resource):
    isLeaf = True

    def __init__(self, service):
        self.service = service

    def render_GET(self, request):
        d = self.service.get_chatroom_list()
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET


class ReportResource(resource.Resource):
    isLeaf = True

    def __init__(self, service, chatroom):
        self.service = service
        self.chatroom = chatroom

    def render_GET(self, request):
        d = self.service.get_log(self.chatroom)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET


class ChatResource(resource.Resource):
    isLeaf = True

    def __init__(self, service, chatroom):
        resource.Resource.__init__(self)
        self.service = service
        self.chatroom = chatroom

    def render_POST(self, request):
        try:
            msg = get_message_from_request(request)
        except Exception as e:
            request.setResponseCode(400)
            request.write("Error in request processing: %r", e)
            request.finish()
            return server.NOT_DONE_YET
        request.setResponseCode(201)
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Credentials', 'true')
        request.setHeader('Content-Type', 'application/json')
        d = self.service.post_message(self.chatroom, msg)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET

    def render_GET(self, request):
        args = request.args
        def _format(msglist):
            result = []
            if msglist:
                for msg in msglist:
                    result.append({'from': msg.from_, 'to': msg.to,
                        'timestamp': msg.timestamp,
                        'body': msg.body,
                        'sender': msg.sender, 'id': msg.id})
            return bytes(json.dumps(result))

        from_time = None
        if args.has_key('from_time'):
            from_time = args['from_time'][0]
        d = self.service.get_messages(self.chatroom, from_time)
        d.addCallback(_format)
        d.addCallback(request.write)
        d.addCallback(lambda _: request.finish())
        return server.NOT_DONE_YET


class AuthenticationResource(resource.Resource):
    isLeaf = True

    def __init__(self, key, service):
        resource.Resource.__init__(self)
        self.key = key
        self.service = service

    def write_request(self, body, request):
        if body:
            request.write(bytes(body))
        else:
            request.setResponseCode(404)
        request.finish()
        return

    def render_GET(self, request):
        '''

        @param request:
        @type request:
        @return: token for which key is registered.
        @rtype:
        '''
        d = self.service.get_contest_id_for_retrieve_id(self.key)
        d.addErrback(log.err)
        d.addCallback(self.write_request, request)
        return server.NOT_DONE_YET


class HandshakeResource(resource.Resource):
    isLeaf = True
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service

    def render_GET(self, request):
        '''
        Return chatroom id for taken token.
        @return: chatroom id
        @rtype: str
        '''
        token = request.getHeader(b'x-app-token')
        d = self.service.authenticate(token)
        d.addErrback(self._trap_auth_error, request)
        d.addCallback(request.write)
        d.addCallback(lambda _:request.finish())
        return server.NOT_DONE_YET

    def _trap_auth_error(self, failure, request):
        failure.trap(AuthenticationError)
        request.setResponseCode(403)
        return ''


class ChatAPI(resource.Resource):
    isLeaf = True

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.operations = dict(person=self.service.get_phone_for_person,
            phone=self.service.get_person_by_phone)

    def render_GET(self, request):
        if len(request.postpath) > 1 and request.postpath[0] and request.postpath[1]:
            operation = request.postpath[0]
            argument = request.postpath[1]
            d = self.operations[operation](argument)
            d.addCallback(request.write)
            d.addCallback(lambda _:request.finish())
            return server.NOT_DONE_YET
        else:
            return ''

