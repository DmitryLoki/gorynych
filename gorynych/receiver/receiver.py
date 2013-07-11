'''
Thinkless copy/paste.
I hope it works.
'''
__author__ = 'Boris Tsema'
import time
from operator import xor
import cPickle
import collections

from twisted.protocols import basic
from twisted.internet import protocol, task, defer, reactor
from twisted.application.service import Service
from twisted.python import log

from pika.connection import ConnectionParameters
from pika.adapters.twisted_connection import TwistedProtocolConnection

################### Network part ###############################################
class ReceivingProtocol(basic.LineReceiver):

    def lineReceived(self, data):
        self.factory.service.handle_message(data, proto='TCP')

class ReceivingFactory(protocol.ServerFactory):

    protocol = ReceivingProtocol

    def __init__(self, service):
        self.service = service


class UDPReceivingProtocol(protocol.DatagramProtocol):

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        self.service.handle_message(datagram, proto='UDP', client=addr)

###################### Different receivers #####################################

class FileReceiver:
    '''This class just write a message to file.'''
    # XXX: do smth clever with interfaces. It's not good to have a class with
    # just __init__ and one method.

    running = 1

    def __init__(self, filename):
        self.filename = filename

    def write(self, data):
        # XXX: this is a blocking operation. It's bad in Twisted. Rework.
        fd = open(self.filename, 'a')
        fd.write(''.join((str(data), '\r\n')))
        fd.close()

class CheckReceiver:
    running = 1
    def __init__(self, filename):
        self.filename = filename
        # imei: time
        self.messages = collections.defaultdict(dict)
        self.coords = collections.defaultdict(dict)

    def write(self, data):
        '''data is a dict with parsed data.'''
        self.messages[data['imei']] = int(time.time())
        self.coords[data['imei']] = (data['lat'], data['lon'], data['alt'],
        data['h_speed'])


class RabbitMQService(Service):
    '''
    This is base service for consuming data from RabbitMQ.
    All other services with the same goals need to be inherited from this one.
    Every service is working with only one exchange.
    '''

    exchange = 'default'
    exchange_type = 'direct'
    durable_exchange = False
    exchange_auto_delete = False

    queue = 'default' # not sure about this
    queues_durable = False
    queue_auto_delete = False
    queues_exclusive = False
    queues_no_ack = False

    def __init__(self, **kw):
    #        pars = parse_parameters(**kw) # TODO: parameters parsing
        # XXX: workaround
        self.pars = kw
        self.exchange = self.pars.get('exchange',
            self.exchange)
        self.durable_exchange = self.pars.get('durable_exchange',
            self.durable_exchange)
        self.exchange_type = self.pars.get('exchange_type',
            self.exchange_type)
        self.exchange_auto_delete = self.pars.get('auto_delete',
            self.exchange_auto_delete)
        self.queue_auto_delete = self.pars.get('auto_delete_queues',
            self.queue_auto_delete)
        self.queues_durable = self.pars.get('queues_durable',
            self.queues_durable)
        self.queues_exclusive = self.pars.get('queues_exclusive',
            self.queues_exclusive)
        self.queues_no_ack = self.pars.get('queues_no_ack',
            self.queues_no_ack)
        self.opened_queues = {}
        self.running_checker = task.LoopingCall(self.__check_if_running)
        self.running_checker.start(0.5)

    def __check_if_running(self):
        if self.running:
            self.when_started()
            self.running_checker.stop()

    def when_started(self):
        '''Override this method if you want to do something after service have been started.'''
        pass

    def startService(self):
        cc = protocol.ClientCreator(reactor, TwistedProtocolConnection,
            ConnectionParameters())
        d = cc.connectTCP(self.pars['host'], self.pars['port'])
        d.addCallback(lambda protocol: protocol.ready)
        d.addCallback(self.__on_connected)
        d.addCallback(lambda _: Service.startService(self))
        d.addCallback(lambda _:log.msg("Service started on exchange %s type %s."
                                       % (self.exchange, self.exchange_type)))

    def stopService(self):
        for queue in self.opened_queues.keys():
            self.channel.queue_delete(queue=queue)
        Service.stopService(self)

    def __on_connected(self, connection):
        log.msg('RabbitmqSender: connected.')
        self.defer = connection.channel()
        self.defer.addCallback(self.__got_channel)
        self.defer.addCallback(self.create_exchange)

    def __got_channel(self, channel):
        log.msg('RabbitmqSender: got the channel.')
        self.channel = channel

    def create_exchange(self, _):
        return self.channel.exchange_declare(
            exchange=self.exchange,
            durable=self.durable_exchange,
            type=self.exchange_type,
            auto_delete=self.exchange_auto_delete)

    def open(self, queue_name, routing_keys=[], mode='r'):
        '''
        Create and bind queue. Add queue object to self.opened_queues.
        Return Deferred instance which return queue name.
        Usage:
        d = open(queue_name)
        d.addCallback(lambda queue_name: handle(queue_name))
        message_from_queue = read(self.opened_queues[queue_name])
        This method us necessary only for consuming, you needn't call this for
        sending messages to RabbitMQ.
        '''
        assert isinstance(queue_name, str), 'Queue name must be a string.'
        assert len(queue_name) > 0, 'Can not use empty string as queue name.'

        keys = self.process_routing_keys(routing_keys)
        log.msg('Routing keys: %s' % keys)
        d = defer.Deferred()
        log.msg("Opening queue", queue_name)
        d.addCallback(self.create_queue)
        d.addCallback(self.bind_queue, keys)
        if mode == 'r':
            d.addCallback(self.start_consuming)
            d.addCallback(self.get_queue, queue_name)
        if mode == 'w':
            d.addCallback(lambda _:log.msg('Opened for writing.'))
        d.addErrback(log.err)
        d.callback(queue_name)
        return d

    def process_routing_keys(self, routing_keys):
        '''
        Check routing keys, return list with keys. Don't use with 'topic'
        exchange type as it has limitation on routing key length and more
        special formatting can be needed.
        '''
        result = []
        if not routing_keys:
            result.append('')
            return result
        elif not isinstance(routing_keys, list):
            result.append(str(routing_keys))
            return result
        else:
            # Getting flat list.
            flatten_list = ','.join(map(str, routing_keys)).split(',')
            log.msg(flatten_list)
        return flatten_list

    def create_queue(self, queue_name):
        log.msg('Creating queue %s' % queue_name)
        return self.channel.queue_declare(
            queue=queue_name,
            auto_delete=self.queue_auto_delete,
            durable=self.queues_durable,
            exclusive=self.queues_exclusive)

    def bind_queue(self, frame, routing_keys):
        for key in routing_keys:
            log.msg('Bind %s with key %s.' % (frame.method.queue, key))
            self.channel.queue_bind(
                queue=frame.method.queue,
                exchange=self.exchange,
                routing_key=key
            )
        log.msg('Queue %s bound.' % frame.method.queue)
        return frame.method.queue

    def start_consuming(self, queue):
        '''Return queue and consumer tag.'''
        log.msg('Start consuming from queue', queue)
        return self.channel.basic_consume(
            queue=queue,
            no_ack=self.queues_no_ack)

    def get_queue(self, queue_and_consumer_tag, queue_name):
        queue, consumer_tag = queue_and_consumer_tag
        if self.opened_queues.has_key(queue_name):
            raise RuntimeError('Queue has been opened already.')
        else:
            self.opened_queues[queue_name] = queue
            return queue_name

    def read(self, queue_name):
        '''Read opened queue.'''
        #        log.msg(self.opened_queues[queue_name])
        d = self.opened_queues[queue_name].get()
        return d.addCallback(lambda  ret: self.handle_payload(queue_name,
            *ret))

    def handle_payload(self, queue_name, channel, method_frame, header_frame, \
            body):
        '''Override this method for doing something usefull.'''
        log.msg("Message received from queue %s: %s" % (queue_name,body))
        #        log.msg('Also received: %s %s %s' % (channel, method_frame,
        #                                             header_frame))
        #        Also received:
        #        <pika.channel.Channel object at 0x101aa4f10>
        #        <Basic.Deliver(['consumer_tag=ctag1.0', 'redelivered=False', 'routing_key=', 'delivery_tag=4', 'exchange=default'])>
        #        <BasicProperties([])>
        return body

    def write(self, data, key='', exchange=''):
        if data:
            exchange = exchange or self.exchange
            # log.msg('write data %s to exchange %s' % (data, exchange))
            self.channel.basic_publish(exchange=exchange,
                routing_key=key,
                body=self.serialize(data))

    def serialize(self, data):
        return str(data)

    def close(self, queue_name):
        '''Close consuming from queue.'''
        del self.opened_queues[queue_name]
        d = self.channel.queue_delete(queue=queue_name)
        d.addErrback(log.err)


class ReceiverRabbitService(RabbitMQService):

    def serialize(self, data):
        return cPickle.dumps(data, protocol=2)


class GlobalSatTR203(object):

    def __init__(self):
        self.format = dict(type = 0, imei = 1, lat = 10, lon = 9, alt = 11,
            h_speed = 12, battery = 16)
        self.convert = dict(type = str, imei = str, lat = self.latitude,
            lon = self.longitude, alt = int, h_speed = self.speed,
            battery = str)

    def speed(self, speed):
        return round(float(speed) * 1.609, 1)

    def latitude(self, lat):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lat = lat[1:3]
        MM_lat = lat[3:5]
        SSSS_lat = float(lat[5:])*60
        if lat[:1] == "N":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lat) + float(MM_lat)/60 +
                                SSSS_lat/3600)[:9])

    def longitude(self, lon):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lon = lon[1:4]
        MM_lon = lon[4:6]
        SSSS_lon = float(lon[6:])*60
        if lon[:1] == "E":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lon) + float(MM_lon)/60 +
                                SSSS_lon/3600)[:9])

    def check_checksum(self, msg):
        """Check checksum of obtained msg."""
        try:
            msg = str(msg)
            nmea = map(ord, msg[:msg.index('*')])
            check = reduce(xor, nmea)
            received_checksum = msg[msg.index('*')+1:msg.index('!')]
            if check == int(received_checksum, 16):
                return msg
            else:
                raise ValueError("Incorrect checksum")
        except Exception as e:
            raise ValueError(str(e))

    def parse(self, msg):
        arr = msg.split('*')[0].split(',')
        if arr[0] == 'GSr':
            result = dict()
            for key in self.format.keys():
                result[key] = self.convert[key](arr[self.format[key]])
            result['ts'] = int(time.mktime(
                time.strptime(''.join((arr[7], arr[8])),'%d%m%y%H%M%S')))
            return result


class ReceiverService(Service):

    cache_expiration = 300

    def __init__(self, sender, audit_log):
        '''
        _uid_cache: {imei: (uid, update_time)}
        '''
        self.sender = sender
        self.audit_log = audit_log
        self.tr203 = GlobalSatTR203()
        self._uid_cache = dict()
        cache_cleaner = task.LoopingCall(self._cache_sweeper)
        cache_cleaner.start(self.cache_expiration, now=False)
        ##### checker
        self.messages = dict()
        self.coords = dict()

    def handle_message(self, msg, **kw):
        '''
        Parse received message.
        Write a message to AuditLog.
        Send a message further.
        '''
        receiving_time = time.time()
        d = defer.maybeDeferred(self.tr203.check_checksum, msg)
        d.addCallbacks(self.audit_log.log_msg,
            self.audit_log.log_err,
            callbackArgs=[],
            callbackKeywords={'time':receiving_time,
                'proto': kw.get('proto', 'Unknown')},
            errbackArgs=[],
            errbackKeywords={'data': msg, 'time': receiving_time,
                'proto': kw.get('proto', 'Unknown')})
        if self.sender.running:
            d.addCallback(self.tr203.parse)
            d.addCallback(self._imei_pilot_filter)
            d.addCallback(self.sender.write)
        else:
            log.msg("Received but not sent: %s" % msg)
        d.addErrback(log.err)

    def _imei_pilot_filter(self, parsed):
        '''
        Take parsed message from parser and change tracker_id to pilot uid.
        '''
        #if parsed['imei'] in self._uid_cache.keys():
        #parsed['uid'] = self._uid_cache[parsed['imei']]
        #else:
        #parsed['uid'] = parsed['imei']
        ###### checker
        self.messages[parsed['imei']] = int(time.time())
        self.coords[parsed['imei']] = (parsed['lat'], parsed['lon'],
        parsed['alt'], parsed['h_speed'], int(time.time()) )
        #        del parsed['imei']
        return parsed

    def _cache_sweeper(self):
        '''Clear _uid_cache.'''
        allowed_time = int(time.time()) - self.cache_expiration
        for key in self._uid_cache.keys():
            if self._uid_cache[key][1] < allowed_time:
                del self._uid_cache[key]


class AuditLog:
    '''Base class for audit logging classes.'''

    def _format(self, **kw):
        result = kw
        timelist = ['time', 'ts', 'timestamp']
        datalist = ['data', 'msg', 'message']
        for key in kw.keys():
            if key in timelist:
                x = int(kw[key])
                del kw[key]
                result['ts'] = x
            if key in datalist:
                x = str(kw[key])
                del kw[key]
                result['msg'] = x
        return result

    def _write_log(self, log_message):
        raise NotImplementedError('You need to implement log writing.')

    def log_err(self, failure, **kw):
        ''' Receive Failure object.'''
        kwargs = kw
        kwargs['err'] = failure.getErrorMessage()
        formatted_msg = self._format(**kwargs)
        self._write_log(formatted_msg)

    def log_msg(self, msg, **kw):
        kwargs = kw
        kwargs['msg'] = msg
        formatted_msg = self._format(**kwargs)
        self._write_log(formatted_msg)
        return msg


class AuditFileLog(AuditLog):
    '''This class log messages to file.'''

    def __init__(self, logname):
        self.name = logname

    def _write_log(self, log_message):
        fd = open(self.name, 'a')
        fd.write(''.join((str(log_message), '\r\n')))
        fd.close()


class DumbAuditLog(AuditLog):
    def _write_log(self, log_message):
        pass
