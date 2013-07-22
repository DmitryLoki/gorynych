'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic


def check_device_type(msg):
    if msg[0] == 'G':
        result = 'tr203'
    else:
        result = 'telt_gh3000'
    return result


class UDPReceivingProtocol(protocol.DatagramProtocol):
    '''
    Unused.
    '''

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        device_type = check_device_type(datagram)
        if device_type == 'telt_gh3000':
            response = self.service.parsers[device_type].get_response(datagram)
            self.transport.write(response, addr)
        self.service.handle_message(datagram, proto='UDP', client=addr,
                                    device_type=device_type)


class ReceivingProtocol(basic.LineReceiver):
    '''
    Line receiver protocol. Used by mobile application.
    '''

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')


class TR203ReceivingProtocol(protocol.Protocol):
    '''
    TCP-receiving protocol for tr203.
    '''

    def dataReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP',
                                            device_type='tr203')


class UDPTR203Protocol(protocol.DatagramProtocol):
    '''
    UDP-receiving protocol for tr203.
    '''
    device_type = 'tr203'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        self.service.handle_message(datagram, proto='UDP',
                                    device_type=self.device_type)


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):
    '''
    UDP receiving protocol for Teltonika GH3000.
    '''
    device_type = 'telt_gh3000'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        response = self.service.parsers[self.device_type].get_response(datagram)
        self.transport.write(response, sender)
        self.service.handle_message(datagram, proto='UDP', client=sender,
                                    device_type=self.device_type)
