DROP SCHEMA IF EXISTS PUBLIC CASCADE;
CREATE SCHEMA PUBLIC;

create table track_type(
  id serial primary key,
  name text not null);
insert into track_type (name) values('competition aftertask');

-- Таблица треков
CREATE TABLE TRACK(
-- Системный ID трека
  ID BIGSERIAL PRIMARY KEY,
-- Дата и время начала трека
  START_TIME integer,
-- Дата и время окончания трека
  END_TIME integer,
-- ID трекера, с которого получен этот трек
  TRACK_ID TEXT UNIQUE NOT NULL,
-- Тип трека
  TRACK_TYPE INT REFERENCES TRACK_TYPE(ID)
);

-- Данные треков
CREATE TABLE TRACK_DATA(
  TRID BIGINT REFERENCES TRACK(ID),
  timestamp integer,
  LAT REAL,
  LON REAL,
  ALT REAL,
  G_SPEED REAL,
  V_SPEED REAL,
  DISTANCE REAL
);
CREATE TABLE TRACK_SNAPSHOT(
  TRID BIGINT REFERENCES TRACK(ID),
  TIMESTAMP integer,
  SNAPSHOT TEXT,

  PRIMARY KEY (TIMESTAMP, TRID)
);

-- Таблица со списком гонок
CREATE TABLE RACE(
-- Системный ID гонки
  ID BIGSERIAL PRIMARY KEY,
-- UUID
  RACE_ID TEXT UNIQUE NOT NULL
-- Отображаемое название гонки
);

create table race_tracks (
  rid BIGINT REFERENCES RACE (ID) ON DELETE CASCADE,
  contest_number text not null,
  track_id text unique,
  PRIMARY KEY (RID, CONTEST_NUMBER)
);

CREATE INDEX track_data_timestamp_idx
ON track_data
USING btree
("timestamp" );
