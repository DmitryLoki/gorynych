'''
Thinkless copy/paste.
I hope it works.
'''

__author__ = 'Boris Tsema'
import time
import cPickle
import collections

from twisted.internet import defer
from twisted.application.service import Service
from twisted.python import log

from gorynych.common.infrastructure.messaging import RabbitMQObject


###################### Different receivers ################################

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


class ReceiverRabbitQueue(RabbitMQObject):
    def serialize(self, data):
        return cPickle.dumps(data, protocol=2)


class ReceiverService(Service):
    def __init__(self, sender, audit_log, parser):
        self.sender = sender
        self.sender.connect()
        self.audit_log = audit_log
        self.parser = parser

    def check_message(self, msg, **kw):
        '''
        Checks message correctness. If correct, logs it, else logs the error.
        '''
        receiving_time = time.time()
        device_type = kw.get('device_type', 'tr203')
        d = defer.succeed(msg)
        d.addCallback(self.parser.check_message_correctness)
        d.addCallbacks(self.audit_log.log_msg,
            self.audit_log.log_err,
            callbackArgs=[],
            callbackKeywords={'time': receiving_time,
                'proto': kw.get('proto', 'Unknown'),
                'device': kw.get('device_type', 'Unknown')},
            errbackArgs=[],
            errbackKeywords={'data': msg, 'time': receiving_time,
                'proto': kw.get('proto', 'Unknown'),
                'device': kw.get('device_type', 'Unknown')})
        if not self.sender.ready:
            log.msg("Received but not sent: %s" % msg)
        d.addErrback(self._handle_error)
        d.addErrback(log.err)
        return d

    def store_point(self, message):
        d = defer.Deferred()
        if isinstance(message, list):
            for item in message:
                # item=item magic is required by lambda to grab item correctly
                # otherwise item is always message[-1]. Do not modify!
                d.addCallback(lambda _, item=item: self.sender.write(item))
        else:
            d.addCallback(lambda _: self.sender.write(message))

        d.callback('go!')
        return d

    def handle_message(self, msg, **kw):
        """
        Backwards compatible method: checks message, parses it, assumes
        that result is a point and stores it.
        """
        result = self.check_message(msg, **kw)
        result.addCallback(self.parser.parse)
        result.addCallback(self.store_point)
        return result

    def _handle_error(self, failure):
        failure.trap(EOFError)


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
        raise EOFError()

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
        fd.write(''.join((bytes(log_message), '\r\n')))
        fd.close()


class DumbAuditLog(AuditLog):
    def _write_log(self, log_message):
        pass


