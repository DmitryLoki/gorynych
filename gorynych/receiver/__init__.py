from twisted.application import service
from twisted.application.internet import TCPServer, UDPServer

from gorynych import BaseOptions


class Options(BaseOptions):
    optParameters = [
        ['protocols', '', None, 'Transport protocol separated by comma. '
                                'TCP or/and UDP allowed.'],
        ['tracker', '', None],
        ['port', 'P', 9999, None, int]
    ]

    def opt_protocols(self, proto):
        self['protocols'] = list(set(proto.lower().split(',')))

    def postOptions(self):
        if self['tracker'] is None:
            raise SystemExit("Tracker type missed.")
        if self['protocols'] is None:
            raise SystemExit("No protocol specified.")
        for proto in self['protocols']:
            if proto not in ['tcp', 'udp']:
                raise SystemExit("Protocol %s not allowed." % proto)


def makeService(config):
    '''
    Create service tree. Only one tracker can be used for every protocol!
    @param config: instance of an Options class with configuration parameters.
    @type config: C{twisted.python.usage.Options}
    @return: service collection
    @rtype: C{twisted.application.service.IServiceCollection}
    '''
    from gorynych.receiver.factories import ReceivingFactory
    from gorynych.receiver import protocols
    from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService, AuditFileLog

    # Set up application.
    application = service.Application("ReceiverServer")
    sc = service.IServiceCollection(application)

    # Prepare receiver.
    audit_log = AuditFileLog('audit_log')
    sender = ReceiverRabbitService(host='localhost', port=5672,
        exchange='receiver', exchange_type='fanout')
    sender.setName('RabbitMQReceiverService')
    sender.setServiceParent(sc)
    receiver_service = ReceiverService(sender, audit_log, config['tracker'])
    receiver_service.setName('ReceiverService')
    receiver_service.setServiceParent(sc)

    if 'tcp' in config['protocols']:
        receiver_server = TCPServer(config['port'],
            ReceivingFactory(receiver_service))
        protocol = getattr(protocols,
            '_'.join((config['tracker'], 'tcp','protocol')))
        receiver_server.args[1].protocol = protocol
        receiver_server.setName(config['tracker'] + '_tcp')
        receiver_server.setServiceParent(sc)

    if 'udp' in config['protocols']:
        protocol = getattr(protocols,
            '_'.join((config['tracker'], 'udp','protocol')))(receiver_service)
        receiver_server = UDPServer(config['port'], protocol)
        receiver_server.setName(config['tracker'] + '_udp')
        receiver_server.setServiceParent(sc)
    return sc
