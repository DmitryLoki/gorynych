'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic


class UDPReceivingProtocol(protocol.DatagramProtocol):

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        self.service.handle_message(datagram, proto='UDP', client=addr)


class ReceivingProtocol(basic.LineReceiver):

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')