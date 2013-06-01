from gorynych.common.domain.events import ArchiveURLReceived

__author__ = 'Boris Tsema'
import re
import time

from twisted.application.service import Service
from twisted.internet import task, reactor
from twisted.python import log


GET_EVENTS = """
    SELECT e.event_name, e.aggregate_id, e.aggregate_type, e.event_payload,
    e.event_id, e.occured_on
    FROM events e, dispatch d
    WHERE event_name = %s  AND e.event_id = d.event_id;
    """

EVENT_DISPATCHED = """
    DELETE FROM dispatch WHERE event_id = %s
    """

class EventPollingService(Service):
    '''
    Start to read events from db on start.
    '''
    def __init__(self, pool):
        self.pool = pool
        self.event_poller = task.LoopingCall(self.poll_for_events)

    def startService(self):
        d = self.pool.start()
        d.addCallback(lambda _: log.msg("DB pool started."))
        d.addCallback(lambda _: self.event_poller.start(2))
        return d.addCallback(lambda _: Service.startService(self))

    def stopService(self):
        self.event_poller.stop()
        Service.stopService(self)
        return self.pool.close()

    def poll_for_events(self):
        d = self.pool.runQuery(GET_EVENTS, ('ArchiveURLReceived',))
        d.addCallback(self.process_events)
        return d

    def process_events(self, event_list):
        while event_list:
            name, aggrid, atype, payload, event_id, occ_on = event_list.pop()
            if name in self.processable_events:
                # TODO: get event class from name.
                ev = ArchiveURLReceived(aggrid, aggregate_type=atype,
                        occured_on=int(time.mktime(occ_on.timetuple())))
                ev.payload = ev.serializer.from_bytes(payload)
                # TODO: realize this.
                ev.id = event_id
                reactor.callLater(0, getattr(self, 'process_'+str(name)), ev)

    @property
    def processable_events(self):
        result = []
        # TODO: too deep, rewrite.
        for item in dir(self):
            item = item.split('_')
            if len(item) == 2:
                if item[0] == 'process':
                    if re.match('[A-Z]', item[1][0]):
                        result.append(item[1])
        return result

    def event_dispatched(self, ev_id):
        ev_id = long(ev_id)
        return self.pool.runOperation(EVENT_DISPATCHED, (ev_id,))
