__author__ = 'Boris Tsema'
from twisted.application import internet, service
from twisted.web.server import Site

from gorynych import BaseOptions

class Options(BaseOptions):
    optParameters = [
        ['protocol', 'p', 'UDP'],
        ['tracker', 't', None],
        ['port', 'P', 9999, None, int],
        ['webport', 'wb', 8084, None, int]
    ]

def makeService(config):
    from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService, AuditFileLog, ReceivingFactory
    from gorynych.receiver.protocols import UDPTR203Protocol, UDPTeltonikaGH3000Protocol
    ####### check_trackers ####
    from gorynych.receiver.online_tester import RetreiveJSON

    # Set up application.
    application = service.Application("ReceiverServer")
    sc = service.IServiceCollection(application)

    # Prepare receiver.
    audit_log = AuditFileLog('audit_log')
    sender = ReceiverRabbitService(host='localhost', port=5672,
        exchange='receiver', exchange_type='fanout')
    receiver_service = ReceiverService(sender, audit_log)
    sender.setServiceParent(sc)
    receiver_service.setServiceParent(sc)

    # Prepare tracker's protocols and servers.
    if not config['tracker']:
        raise SystemExit("Tracker type missed.")

    if config['tracker'] == 'tr203':
        tr203_tcp = internet.TCPServer(
            config['port'], ReceivingFactory(receiver_service))
        tr203_tcp.setServiceParent(sc)

        tr203_udp = UDPTR203Protocol(receiver_service)
        tr203_udp_receiver = internet.UDPServer(
            config['port'], tr203_udp)
        tr203_udp_receiver.setServiceParent(sc)

    elif config['tracker'] == 'telt_gh3000':
        telt_udp = UDPTeltonikaGH3000Protocol(receiver_service)
        telt_udp_receiver = internet.UDPServer(config['port'], telt_udp)
        telt_udp_receiver.setServiceParent(sc)

    root = RetreiveJSON(receiver_service)
    internet.TCPServer(config['webport'], Site(root)).setServiceParent(sc)

    return sc

