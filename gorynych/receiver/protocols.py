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

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        device_type = check_device_type(datagram)
        if device_type == 'telt_gh3000':
            response = self.service.parsers[device_type].get_response(
                datagram)
        self.service.handle_message(datagram, proto='UDP', client=addr,
            device_type=device_type)
        if device_type == 'telt_gh3000':
            self.transport.write(response, addr)


class ReceivingProtocol(basic.LineReceiver):

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):
    device_type = 'telt_gh3000'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        self.service.handle_message(datagram, proto='UDP', client=sender,
            device_type=self.device_type)
        response = self.service.parsers[self.device_type].get_response()
        self.transport.write(response, sender)
