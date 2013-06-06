import uuid
import time
from datetime import datetime

from twisted.trial import unittest
from twisted.internet import defer
from twisted.enterprise import adbapi

from gorynych.eventstore import store
from gorynych import OPTS


def print_result(result):
    print result

store.EVENTS_TABLE = EVENTS_TABLE = 'test_events'
store.FUNC_NAME = FUNC_NAME = 'test_trigger'
store.DISPATCH_TABLE = DISPATCH_TABLE = 'test_dispatch'
store.TRIGGER_NAME = TRIGGER_NAME = 'test_to_dispatch'

def create_serialized_event(ts=None, id=None):
    result = dict()
    result['event_name'] = 'event_name'
    if not id:
        id = str(uuid.uuid4())
    result['aggregate_id'] = str(id)
    result['aggregate_type'] = 'TestAggregate'
    result['event_payload'] = bytes('payload')
    if not ts:
        ts = int(time.time())
    result['occured_on'] = datetime.fromtimestamp(ts)
    return result

POOL = adbapi.ConnectionPool('psycopg2', host=OPTS['db']['host'],
    database=OPTS['db']['database'], user=OPTS['db']['user'],
    password=OPTS['db']['password'])

class PGSQLAOSInitTest(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        self.pool = POOL
        self.pool.start()
        yield self.pool.runOperation('drop table if exists "%s" CASCADE',
                                     (EVENTS_TABLE,))
        yield self.pool.runOperation('drop table if exists "%s"',
                                     (DISPATCH_TABLE,))
        yield self.pool.runOperation('drop function if exists {f}() CASCADE'
            .format(f=FUNC_NAME))

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.pool.runOperation('drop table if exists "%s" CASCADE',
                                     (EVENTS_TABLE,))
        yield self.pool.runOperation('drop table if exists "%s"',
                                     (DISPATCH_TABLE,))
        yield self.pool.runOperation('drop function if exists {f}() CASCADE'
        .format(f=FUNC_NAME))

    @defer.inlineCallbacks
    def test_init(self):
        aos = store.PGSQLAppendOnlyStore(self.pool)
        yield aos.initialize()
        tables = yield self.pool.runQuery(
            "SELECT tablename FROM pg_catalog.pg_tables;")
        self.assertTrue((EVENTS_TABLE,) in tables,
                        "Events table hasn't been created.")
        self.assertTrue((DISPATCH_TABLE,) in tables,
                        "Dispatch table hasn't been created.")
        trigger = yield self.pool.runQuery(
            "select * from pg_trigger where tgname like %s", (TRIGGER_NAME,))
        self.assertTrue(TRIGGER_NAME in trigger[0])
        func = yield self.pool.runQuery("select * from pg_proc where "
                                        "proname=%s", (FUNC_NAME,))
        self.assertTrue(FUNC_NAME in func[0])


class PGSQLAOSTest(unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):
        self.pool = POOL
        self.pool.start()
        self.store = store.PGSQLAppendOnlyStore(self.pool)
        yield self.pool.runOperation('drop table if exists "%s" CASCADE;',
                                     (EVENTS_TABLE,))
        yield self.pool.runOperation('drop table if exists "%s";',
                                     (DISPATCH_TABLE,))
        yield self.pool.runOperation('drop function if exists {f}() CASCADE;'
        .format(f=FUNC_NAME))
        yield self.store.initialize()

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.pool.runOperation('drop table if exists %s CASCADE;' %
                                     EVENTS_TABLE)
        yield self.pool.runOperation('drop table if exists %s;' %
                                     DISPATCH_TABLE)
        yield self.pool.runOperation('drop function if exists {f}() CASCADE;'
        .format(f=FUNC_NAME))

    @defer.inlineCallbacks
    def test_append(self):
        ts = int(time.time())
        id = str(uuid.uuid4())
        ser_event = create_serialized_event(ts=ts, id=id)
        yield self.store.append([ser_event, ser_event])

        stored_event = yield self.pool.runQuery(
            "select * from {tbl} where aggregate_id like %s".format(
                tbl=EVENTS_TABLE), (id,))
        self.assertEqual(len(stored_event), 2)
        eid, sname, sid, stype, spayload, sts = stored_event[0]
        self.assertTupleEqual((sname, sid, stype, str(spayload), sts),
            ('event_name', id, 'TestAggregate', 'payload',
            datetime.fromtimestamp(ts)), "Event hasn't been saved correctly.")

        eid2, sname2, sid2, stype2, spayload2, sts2 = stored_event[1]
        self.assertTupleEqual((sname2, sid2, stype2, str(spayload2), sts2),
            ('event_name', id, 'TestAggregate', 'payload',
            datetime.fromtimestamp(ts)), "Event hasn't been saved correctly.")

        nondispatched_event = yield self.pool.runQuery("select * from {tbl} "
                   "where event_id=%s".format(tbl=DISPATCH_TABLE), (eid,))
        defer.returnValue(self.assertEqual(long(eid),
            nondispatched_event[0][0]))

    @defer.inlineCallbacks
    def test_load_events(self):
        # Can fail if test_append fail.
        ts = int(time.time())
        # id = str(uuid.uuid4())
        id = '4'
        ser_event = create_serialized_event(ts=ts, id=id)
        yield self.store.append([ser_event])
        stored_event = yield self.store.load_events(id)
        self.assertEqual(len(stored_event), 1)
        self.assertEqual(stored_event[0][2], id)
