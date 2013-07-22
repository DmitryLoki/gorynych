from twisted.application.service import ServiceMaker

receiver = ServiceMaker('Receiver', 'gorynych.receiver', 'Receiving socket server.', 'greceiver')
