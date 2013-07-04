# coding=utf-8
from collections import defaultdict
from zope.interface import implementer
from twisted.python import log

from gorynych.eventstore.interfaces import IAppendOnlyStore

CREATE_EVENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS {events_table}
    (
      -- Сквозной номер события, нужен для publishing события в queue.
      EVENT_ID bigserial PRIMARY KEY,
      -- Имя события (имя класса).
      EVENT_NAME TEXT NOT NULL,
      -- Идентификатор агрегата.
      AGGREGATE_ID TEXT NOT NULL,
      -- тип агрегата
      AGGREGATE_TYPE TEXT NOT NULL,
      -- Содержимое события.
      EVENT_PAYLOAD BYTEA NOT NULL,
      -- Временная метка события.
      OCCURED_ON TIMESTAMP NOT NULL
    );
    """

CREATE_DISPATCH_TABLE = """
    -- Таблица, в которой хранятся идентификаторы неопубликованных событий.
    CREATE TABLE IF NOT EXISTS {dispatch_table} (
    -- Идентификатор события
    EVENT_ID bigint NOT NULL,

      TAKEN BOOLEAN DEFAULT FALSE ,
      TIME TIMESTAMP DEFAULT NOW(),

  PRIMARY KEY (EVENT_ID)
    );
    """

INSERT_INTO_EVENTS = """
    INSERT INTO {events_table}
    (EVENT_NAME, AGGREGATE_ID, AGGREGATE_TYPE, EVENT_PAYLOAD, OCCURED_ON)
    VALUES (%s, %s, %s, %s, %s);
    """

READ_EVENTS = """
    SELECT * FROM {events_table}
      WHERE AGGREGATE_ID = %s
      ORDER BY OCCURED_ON ASC;
    """

CREATE_TRIGGER = """
    CREATE OR REPLACE FUNCTION {func_name}() RETURNS TRIGGER AS $$
        BEGIN
          INSERT INTO {dispatch_table} (EVENT_ID) VALUES (NEW.EVENT_ID);
          RETURN NEW;
        END;
    $$ LANGUAGE plpgsql;
    """

ADD_TRIGGER = """
    CREATE TRIGGER {trigger_name}
    AFTER INSERT ON {events_table}
    FOR EACH ROW EXECUTE PROCEDURE {func_name}();
    """

GET_UNDISPATCHED_EVENTS = """
    SELECT e.event_id, e.event_name, e.aggregate_id, e.aggregate_type,
    e.event_payload, e.occured_on
    FROM {events_table} e, {dispatch_table} d
    WHERE e.event_id = d.event_id
        AND d.taken = false
        ORDER BY d.time
        LIMIT 5
        FOR UPDATE;
    """

GET_EVENTS_FOR_AGGREGATES = """
    SELECT * FROM {events_table}
    WHERE AGGREGATE_ID in %s

    """


EVENTS_TABLE = 'events'
FUNC_NAME = 'add_to_dispatch'
DISPATCH_TABLE = 'dispatch'
TRIGGER_NAME = 'to_dispatch'


@implementer(IAppendOnlyStore)
class PGSQLAppendOnlyStore(object):
    '''
    Implement L{IAppendOnlyStore} using PostgreSQL DB.
    '''
    def __init__(self, pool):
        self.pool = pool

    def initialize(self):
        def interaction(cur):
            log.msg("Creating events table if not exists...")
            cur.execute(CREATE_EVENTS_TABLE.format(
                                                events_table=EVENTS_TABLE))
            log.msg("Creating dispatch table if not exists...")
            cur.execute(CREATE_DISPATCH_TABLE.format(
                dispatch_table=DISPATCH_TABLE))
            log.msg("Creating or replacing function if not exists...")
            cur.execute(CREATE_TRIGGER.format(
                func_name=FUNC_NAME, dispatch_table=DISPATCH_TABLE))
            log.msg("Dropping trigger if exists...")
            cur.execute(
                "drop trigger if exists {trigger_name} "
                   "on {events_table}".format(trigger_name=TRIGGER_NAME,
                                              events_table=EVENTS_TABLE))
            log.msg("Adding trigger to events table...")
            cur.execute(ADD_TRIGGER.format(
                trigger_name=TRIGGER_NAME, func_name=FUNC_NAME,
                events_table=EVENTS_TABLE))
            log.msg("PGSQL store initialized.")
        return self.pool.runInteraction(interaction)

    def append(self, serialized_event):
        '''
        Append events from stream to store.
        @param serialized_event:
        @type serialized_event: C{list}
        @return:
        @rtype:
        '''
        def interaction(cur, evlist):
            for ev in evlist:
                insert = cur.mogrify(INSERT_INTO_EVENTS.format(
                                            events_table=EVENTS_TABLE), (
                                           ev['event_name'],
                                           ev['aggregate_id'],
                                           ev['aggregate_type'],
                                           ev['event_payload'],
                                           ev['occured_on']))
                cur.execute(insert)
            return
        assert isinstance(serialized_event, list), "AOStore wait for a list."
        evlist = []
        for ev in serialized_event:
            self._check_event(ev)
            evlist.append(ev)
        return self.pool.runInteraction(interaction, evlist)

    def _check_event(self, ev):
        columns = ['event_name', 'aggregate_id',
            'aggregate_type', 'event_payload', 'occured_on']
        for col in columns:
            if not ev.has_key(col):
                raise KeyError("Argument %s is missed" % col)

    def load_events(self, aggregate_id):
        '''

        @param aggregate_id:
        @type aggregate_id:
        @return:
        @rtype: C{list}
        '''
        return self.pool.runQuery(READ_EVENTS.format(
                            events_table=EVENTS_TABLE), (aggregate_id,))

    def load_undispatched_events(self):
        def get_events(cur):
            cur.execute(GET_UNDISPATCHED_EVENTS.format(events_table=EVENTS_TABLE, dispatch_table=DISPATCH_TABLE))
            rows = cur.fetchall()
            ids = []
            for row in rows:
                ids.append(row[0])
            for id in ids:
                cur.execute("UPDATE "+DISPATCH_TABLE+" SET TAKEN=TRUE "
                            "WHERE event_id=%s" % (id,))
            return rows
        return self.pool.runInteraction(get_events)

    def load_events_for_aggregates(self, ags):
        assert isinstance(ags, list)
        def process_list(rows):
            result = defaultdict(list)
            for row in rows:
                _id, _n, _aid, _atype, _payload, _ts = row
                result[_aid].append(row)
            return result

        d = self.pool.runQuery(GET_EVENTS_FOR_AGGREGATES.format(
            events_table=EVENTS_TABLE), [tuple(ags)])
        d.addCallback(process_list)
        return d

