from twisted.application import internet, service
from twisted.web.server import Site


from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService, AuditFileLog, ReceivingFactory
from gorynych.receiver.protocols import UDPReceivingProtocol
####### check_trackers ####
from gorynych.receiver.online_tester import RetreiveJSON

audit_log = AuditFileLog('audit_log')
sender = ReceiverRabbitService(host='localhost', port=5672,
    exchange='receiver', exchange_type='fanout')
receiver_service = ReceiverService(sender, audit_log)

application = service.Application("ReceiverServer")
sc = service.IServiceCollection(application)

sender.setServiceParent(sc)
receiver_service.setServiceParent(sc)

tcp_receiver = internet.TCPServer(5555, ReceivingFactory(receiver_service))
tcp_receiver.setServiceParent(sc)

udp_server = UDPReceivingProtocol(receiver_service)
udp_receiver = internet.UDPServer(9999, udp_server)
udp_receiver.setServiceParent(sc)

root = RetreiveJSON(receiver_service)
internet.TCPServer(8084, Site(root)).setServiceParent(sc)
