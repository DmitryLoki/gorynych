-- Таблица с треками
CREATE TABLE IF NOT EXISTS track
(
  ID BIGSERIAL PRIMARY KEY ,
  START_TIME INTEGER ,
  END_TIME INTEGER ,
  TRACK_TYPE INTEGER REFERENCES TRACK_TYPE (ID) ON DELETE CASCADE,
  TRACK_ID TEXT
);

-- Таблица с типами треков
CREATE TABLE IF NOT EXISTS track_type
(
  ID SERIAL PRIMARY KEY ,
  -- Имя типа треков: freefly, competition live, competition aftertask, free
  NAME TEXT NOT NULL
);

-- Заполнение таблицы с типами
INSERT INTO track_type (name) VALUES ('competition aftertask');

-- Таблица с данными трека
CREATE TABLE IF NOT EXISTS track_data
(
  ID BIGINT REFERENCES TRACK (ID) ON DELETE CASCADE,
  TIMESTAMP INTEGER NOT NULL,
  LAT REAL NOT NULL,
  LON REAL NOT NULL,
  -- Высота в метрах. 32767 метра более чем достаточно
  ALT SMALLINT NOT NULL,
  -- Скорость по земле в км/ч
  G_SPEED REAL,
  -- Вертикальная скорость м/с
  V_SPEED REAL,
  -- Дистанция в метрах
  DISTANCE INTEGER,
  PRIMARY KEY (id, timestamp)
) WITH (OIDS=FALSE);

-- select tracks data
SELECT
  t.timestamp,
  string_agg(
	concat_ws(',', tr.contest_number, t.lat::text, t.lon::text, t.alt::text, t.v_speed::text, t.g_speed::text, t.distance::text),
  ';')
FROM track_data AS t JOIN
	(
	SELECT
	  r2.id AS id, r1.contest_number
	FROM
	  race_tracks r1,
	  track r2,
	  race
	WHERE
	  race.race_id = %s AND
	  r1."RID" = race.id AND
	  r1.track_id = r2.track_id
	) tr
 ON (t.id = tr.id)
WHERE
  t.timestamp BETWEEN %s AND %s
GROUP BY
  t.timestamp
ORDER BY
  t.timestamp;

-- Попытка выбрать данные для заголовка селектом, не используя функцию.
-- Попытка успешная, но не разделяются финишировавшие и севшие пилоты,
-- плюс ещё не стартовавшие пилоты не показываются,
-- плюс перебирается большое количество строк.
WITH rows as (
SELECT
  td."timestamp",
  concat_ws(',',rt.contest_number, td.lat::text, td.lon::text, td.alt::text, td.g_speed::text, td.v_speed::text, td.distance::text,
	case
		when td."timestamp">=tr.end_time then 'landed'
		else 'flying'
	end
	),
  row_number() over(partition by tr.track_id ORDER BY td.timestamp DESC) AS rk
  --tr.track_id
FROM
  public.track tr,
  public.track_data td,
  race_tracks rt
WHERE
  rt."RID" = 15 AND
  rt.track_id = tr.track_id AND
  tr.id = td.id AND
  td."timestamp" < 1347717342
)
select r.timestamp, string_agg(r.concat_ws, ';')
from rows r
where r.rk=1
group by r.timestamp;

-- Выбор треков из временного диапазона.
-- Вернёт (timestamp, data, contest_number)
WITH ids AS (
	SELECT
	  tr.id AS id,
	  race_tracks.contest_number
	FROM
	  public.track tr,
	  public.race_tracks
	WHERE
	  race_tracks.track_id = tr.track_id AND
	  race_tracks."RID" = 15),

      tdata AS (
        SELECT
          timestamp,
          concat_ws(',', lat::text, lon::text, alt::text, g_speed::text, v_speed::text) as data,
          id,
          row_number() OVER(PARTITION BY td.id ORDER BY td.timestamp DESC) AS rk
        FROM track_data td
        WHERE
          td.id in (SELECT id FROM ids)
          AND td."timestamp" BETWEEN 1347717300 AND 1347717342)

SELECT
  t.timestamp, t.data, i.contest_number
FROM
  tdata t,
  ids i
WHERE
  t.rk = 1 AND
  i.id = t.id;

-- Выбор последних снимков для треков. Вернёт (contest_number, snapshot)
WITH ids AS (
	SELECT
	  tr.id AS id,
	  race_tracks.contest_number
	FROM
	  track tr,
	  race_tracks,
    race
	WHERE
	  race_tracks.track_id = tr.track_id AND
	  race_tracks."RID" = 15),

      snaps AS (
	SELECT
	  snapshot,
	  ts.trid AS id,
	  row_number() OVER(PARTITION BY ts.trid ORDER BY ts.timestamp DESC) AS rk
	FROM track_snapshot ts
	WHERE
	  ts.trid in (SELECT id FROM ids))
    AND ts.timestamp <= %s

SELECT
  i.contest_number, s.snapshot
FROM
  snaps s,
  ids i
WHERE
  s.rk = 1
  AND s.id = i.id;