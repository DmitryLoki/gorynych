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
    '''
    Create service tree.
    @param config: instance of an Options class with configuration parameters.
    @type config: C{twisted.python.usage.Options}
    @return: service collection
    @rtype: C{twisted.application.service.IServiceCollection}
    '''
    from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService, AuditFileLog,\
                                           TR203ReceivingFactory, MobileReceivingFactory, \
                                           App13ReceivingFactory, SBDMobileReceivingFactory, \
                                           GT60ReceivingFactory, PmtrackerReceivingFactory
    from gorynych.receiver.protocols import UDPTR203Protocol, UDPTeltonikaGH3000Protocol, HttpTR203Resource
    ####### check_trackers ####
    from gorynych.receiver.online_tester import RetreiveJSON

    # Set up application.
    application = service.Application("ReceiverServer")
    sc = service.IServiceCollection(application)

    # Prepare receiver.
    audit_log = AuditFileLog('audit_log')
    sender = ReceiverRabbitService(host='localhost', port=5672,
        exchange='receiver', exchange_type='fanout')
    sender.setName('ReceiverRabbitService')
    sender.setServiceParent(sc)
    receiver_service = ReceiverService(sender, audit_log)
    receiver_service.setName('ReceiverService')
    receiver_service.setServiceParent(sc)

    # Prepare tracker's protocols and servers.
    if not config['tracker']:
        raise SystemExit("Tracker type missed.")

    if config['tracker'] == 'tr203':
        tr203_tcp = internet.TCPServer(
            config['port'], TR203ReceivingFactory(receiver_service))
        tr203_tcp.setName('tr203_tcp')
        tr203_tcp.setServiceParent(sc)

        tr203_udp = UDPTR203Protocol(receiver_service)
        tr203_udp_receiver = internet.UDPServer(
            config['port'], tr203_udp)
        tr203_udp_receiver.setName('tr203_udp')
        tr203_udp_receiver.setServiceParent(sc)

    elif config['tracker'] == 'telt_gh3000':
        telt_udp = UDPTeltonikaGH3000Protocol(receiver_service)
        telt_udp_receiver = internet.UDPServer(config['port'], telt_udp)
        telt_udp_receiver.setName('telt_gh3000_udp')
        telt_udp_receiver.setServiceParent(sc)

    elif config['tracker'] == 'mobile':
        mob_tcp = internet.TCPServer(
            config['port'], MobileReceivingFactory(receiver_service))
        mob_tcp.setServiceParent(sc)

    elif config['tracker'] == 'app13':
        mob_tcp = internet.TCPServer(
            config['port'], App13ReceivingFactory(receiver_service))
        mob_tcp.setName('app13_tcp')
        mob_tcp.setServiceParent(sc)

    elif config['tracker'] == 'new_mobile_sbd':
        mob_tcp = internet.TCPServer(
            config['port'], SBDMobileReceivingFactory(receiver_service))
        mob_tcp.setServiceParent(sc)

    elif config['tracker'] == 'http':
        site_factory = Site(HttpTR203Resource(receiver_service))
        internet.TCPServer(config['port'], site_factory,
                           interface='localhost').setServiceParent(sc)

    elif config['tracker'] == 'gt60':
        mob_tcp = internet.TCPServer(
            config['port'], GT60ReceivingFactory(receiver_service))
        mob_tcp.setName('gt60_tcp')
        mob_tcp.setServiceParent(sc)

    elif config['tracker'] == 'pmtracker':
        mob_tcp = internet.TCPServer(
            config['port'], PmtrackerReceivingFactory(receiver_service))
        mob_tcp.setServiceParent(sc)

    root = RetreiveJSON(receiver_service)
    web_server = internet.TCPServer(config['webport'], Site(root))
    web_server.setName('WebLog')
    web_server.setServiceParent(sc)

    return sc
