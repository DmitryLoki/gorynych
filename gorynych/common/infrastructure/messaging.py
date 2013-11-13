'''
Base classes for messaging infrastructure.
'''
from pika import ConnectionParameters
from pika.adapters import TwistedProtocolConnection
from twisted.application.service import Service
from twisted.internet import protocol, reactor, defer
from twisted.python import log


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

    def startService(self):
        cc = protocol.ClientCreator(reactor, TwistedProtocolConnection,
            ConnectionParameters())
        d = cc.connectTCP(self.pars['host'], self.pars['port'])
        d.addCallback(lambda protocol: protocol.ready)
        d.addCallback(self.__on_connected)
        d.addCallback(lambda _: Service.startService(self))
        d.addCallback(lambda _:log.msg("Service started on exchange %s type %s."
                                       % (self.exchange, self.exchange_type)))
        d.addCallback(lambda _:self.when_started)
        return d

    def when_started(self):
        '''
        This method will be executed after service start.
        '''
        pass

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

    def handle_payload(self, queue_name, channel, method_frame, header_frame,
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


class FakeRabbitMQService(object):
    """
    This is a special class to test classes derived from RabbitMQService.
    Put your derived class as an argument to the constructor and you'll get the
    patched version of it so you can send and read messages without touching
    any actual RabbitMQ mechanics.

    Don't know where to put it. Let it be here for a while.
    """

    def __new__(self, derived_class):
        import mock
        import types

        def mock_write(target, data, key='', exchange=''):
            target.storage = data

        def mock_read(target, queue_name):
            return target.storage

        with mock.patch.object(derived_class, '__init__') as patched:
            patched.return_value = None
            instance = derived_class()
            instance.write = types.MethodType(mock_write, instance)
            instance.read = types.MethodType(mock_read, instance)
            return instance