from twisted.application.service import Service
from twisted.python import log
from twisted.internet import task, reactor


GET_EVENTS = """
    SELECT e.event_name, e.aggregate_id, e.event_payload
    FROM events e, dispatch d
    WHERE (event_name = %s OR event_name = %s) AND e.event_id = d.event_id;
    """

class TrackService(Service):
    '''
    TrackService parse track archive.
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
        d = self.pool.close()
        d.addCallback(lambda _: self.event_poller.stop())
        return d.addCallback(lambda _: Service.stopService(self))

    def poll_for_events(self):
        d = self.pool.runQuery(GET_EVENTS, ('ArchiveURLReceived',
                                                        'TrackArchiveParsed'))
        d.addCallback(self.process_events)
        return d

    def process_events(self, events):
        while events:
            name, aggrid, payload = events.pop()
            reactor.callLater(0, getattr(self, 'process_'+str(name)),
                aggrid, payload)

    def process_ArchiveURLReceived(self, aggregate_id, payload):
        pass

