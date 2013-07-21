from twisted.application import internet, service
from twisted.web.server import Site


from gorynych.receiver.receiver import ReceiverRabbitService, ReceiverService, AuditFileLog, ReceivingFactory
from gorynych.receiver.protocols import UDPTR203Protocol, UDPTeltonikaGH3000Protocol
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

tcp_receiver = internet.TCPServer(9999, ReceivingFactory(receiver_service))
tcp_receiver.setServiceParent(sc)

white_server = UDPTR203Protocol(receiver_service)
white_receiver = internet.UDPServer(9999, white_server)
white_receiver.setServiceParent(sc)

black_server = UDPTeltonikaGH3000Protocol(receiver_service)
black_receiver = internet.UDPServer(10000, black_server)
black_receiver.setServiceParent(sc)

root = RetreiveJSON(receiver_service)
internet.TCPServer(8084, Site(root)).setServiceParent(sc)
