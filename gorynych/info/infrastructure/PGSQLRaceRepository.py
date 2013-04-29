#! /usr/bin/python
#coding=utf-8
from twisted.internet import defer
import simplejson as json

from zope.interface.declarations import implements
from gorynych.info.domain.race import IRaceRepository, RaceFactory
from gorynych.common.exceptions import NoAggregate
from gorynych.common.domain.types import Checkpoint

SQL_SELECT_RACE = """
SELECT
 RACE_ID,
 TITLE,
 START_TIME,
 END_TIME,
 MIN_START_TIME,
 MAX_END_TIME,
 RACE_TYPE,
 CHECKPOINTS,
 ID
 FROM RACE
 WHERE RACE_ID = %s
"""

SQL_INSERT_RACE = """
INSERT INTO RACE (
 TITLE,
 START_TIME,
 END_TIME,
 MIN_START_TIME,
 MAX_END_TIME,
 RACE_TYPE,
 CHECKPOINTS,
 RACE_ID
)
 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 RETURNING ID
"""

SQL_UPDATE_RACE = """
UPDATE RACE SET
 TITLE = %s,
 START_TIME = %s,
 END_TIME = %s,
 MIN_START_TIME = %s,
 MAX_END_TIME = %s,
 RACE_TYPE = %s,
 CHECKPOINTS = %s
 WHERE RACE_ID = %s
"""


class PGSQLRaceRepository(object):
    implements(IRaceRepository)

    def __init__(self, pool):
        self.pool = pool
        self.factory = RaceFactory()

    @defer.inlineCallbacks
    def get_by_id(self, race_id):
        data = yield self.pool.runQuery(SQL_SELECT_RACE, (race_id,))
        if not data:
            raise NoAggregate("Race")
        result = self._create_race(data[0])
        defer.returnValue(result)

    def _create_race(self, data_row):
        result = self.factory.create_race(
            data_row[1],  # TITLE
            data_row[6],  # RACE_TYPE
            (data_row[4], data_row[5]),  # MIN_START_TIME, MAX_END_TIME
            data_row[0]   # RACE_ID
        )
        result._start_time = data_row[2]  # START_TIME
        result._end_time = data_row[3]  # END_TIME
        self._load_checkpoints_from_json(result, data_row[7])  # CHECKPOINTS
        result._id = data_row[8]  # ID
        return result

    def _load_checkpoints_from_json(self, race, text_value):
        items = json.loads(text_value)
        # TODO перебрать все записи JSON и из каждой сформировать Checkpoint
        checkpoint_list = items["features"]
        for item in checkpoint_list:
            checkpoint = Checkpoint()
            checkpoint.from_geojson(item)
            race.checkpoints.append(checkpoint)

    def store_checkpoints_to_json(self, race):
        checkpoints = []
        for checkpoint in race.checkpoints:
            checkpoints.append(checkpoint.__geo_interface__())
            # TODO перебрать все и сформировать из каждого JSON
        result = dict()
        result["type"] = "FeatureCollection"
        result["features"] = checkpoints
        return json.dumps(result)

    def _params(self, race=None):
        if race is None:
            return ()
        return (race.title, race._start_time, race._end_time,
            race.timelimits[0], race.timelimits[1], race.type(),
            race.checkpoints()
        )

    def save(self, value):
        d = None
        if value._id is not None:
            d = self.pool.runOperation(SQL_UPDATE_RACE,
                                       self._params(value, True))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_RACE, self._params(value))
            d.addCallback(self._process_insert_result, value)
        return d
