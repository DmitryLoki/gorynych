from twisted.internet.protocol import ServerFactory

class ReceivingFactory(ServerFactory):
    '''
    Superclass for factories which are just hold link to service.
    '''
    def __init__(self, service):
        self.service = service
