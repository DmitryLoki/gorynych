'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic

class UDPReceivingProtocol(protocol.DatagramProtocol):
    device_type = 'tr203'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        self.service.handle_message(datagram, proto='UDP', client=addr,
            device_type=self.device_type)


class ReceivingProtocol(basic.LineReceiver):

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):
    device_type = 'telt_gh3000'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        response = self.service.parsers[self.device_type].get_response(
                                                            datagram)
        self.service.handle_message(datagram, proto='UDP', client=sender,
            device_type=self.device_type)
        self.transport.write(response, sender)
