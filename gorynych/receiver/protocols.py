'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic
from parsers import TeltonikaGH3000UDP
import logging
import traceback

class UDPReceivingProtocol(protocol.DatagramProtocol):

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        self.service.handle_message(datagram, proto='UDP', client=addr)


class ReceivingProtocol(basic.LineReceiver):

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')

class UDPTeltonikaGH3000(protocol.DatagramProtocol):
    def __init__(self):
        # get rid of it later
        logging.basicConfig(filename='tracker.log', level=logging.INFO)
        self.parser = TeltonikaGH3000UDP()


    def datagramReceived(self, datagram, sender):
        try:
            data, response = self.parser.parse(datagram)
            self.transport.write(response, sender)
            logging.info(data)
        except Exception as e:
            trc = traceback.format_exc()
            logging.error(trc)
