import simplejson as json
from zope.interface import implementer
from twisted.web import resource, server
# from twisted.internet import defer
from twisted.web.http import stringToDatetime



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
        d = self.service.post_message(self.chatroom, msg)
        d.addCallback(request.write)
        d.addCallback(lambda _:request.finish())
        return server.NOT_DONE_YET

    def render_GET(self, request):
        modified_since = request.getHeader(b'if-modified-since')
        if modified_since:
            first_part = modified_since.split(b';', 1)[0]
            try:
                modified_since = stringToDatetime(first_part)
            except ValueError:
                modified_since = None
        def set_header(msglist):
            if msglist:
                ts = msglist[-1].timestamp
                request.setLastModified(ts)
            return msglist
        def _format(msglist):
            result = []
            if msglist:
                for msg in msglist:
                    result.append({'from': msg.from_, 'to':msg.to,
                        'timestamp': msg.timestamp,
                        'body':msg.body,
                        'sender':msg.sender, 'id':msg.id})
            return bytes(json.dumps(result))
        d = self.service.get_messages(self.chatroom, modified_since)
        d.addCallback(set_header)
        d.addCallback(_format)
        d.addCallback(request.write)
        d.addCallback(lambda _:request.finish())
        return server.NOT_DONE_YET


