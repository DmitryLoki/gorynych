__author__ = 'Boris Tsema'

from twisted.application.service import Service
from twisted.internet import task, reactor
from twisted.python import log


EVENT_DISPATCHED = """
    DELETE FROM dispatch WHERE event_id = %s
    """

class EventPollingService(Service):
    '''
    Start to read events from db on start.
    '''
    polling_interval = 2
    def __init__(self, pool, event_store):
        self.pool = pool
        self.event_store = event_store
        self.event_poller = task.LoopingCall(self.poll_for_events)

    def startService(self):
        self.pool.start()
        log.msg("DB pool started.")
        self.event_poller.start(self.polling_interval)
        Service.startService(self)
        log.msg("EventPollinService %s started." % self.__class__.__name__)

    def stopService(self):
        self.event_poller.stop()
        Service.stopService(self)
        return self.pool.close()

    def poll_for_events(self):
        d = self.event_store.load_undispatched_events()
        d.addCallback(self.process_events)
        return d

    def process_events(self, event_list):
        while event_list:
            ev = event_list.pop()
            evname = ev.__class__.__name__
            attr = 'process_' + evname
            if hasattr(self, attr):
                log.msg("Calling %s in %s" % (attr,
                                            self.__class__.__name__))
                reactor.callLater(0, getattr(self, attr), ev)

    def event_dispatched(self, ev_id):
        ev_id = long(ev_id)
        log.msg("deleting dispatched event", ev_id)
        return self.pool.runOperation(EVENT_DISPATCHED, (ev_id,))
