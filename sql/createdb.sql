DROP SCHEMA IF EXISTS PUBLIC CASCADE;
CREATE SCHEMA PUBLIC;

-- Aggregate Tracker -------------------------------------------

CREATE TABLE DEVICE_TYPE(
	ID BIGSERIAL PRIMARY KEY,
	NAME TEXT
);

CREATE TABLE TRACKER(
-- системный ID трекера
  ID BIGSERIAL PRIMARY KEY,
  DEVICE_ID TEXT NOT NULL,
  -- запретить удаление типа, если трекер для него уже есть
  DEVICE_TYPE BIGINT REFERENCES DEVICE_TYPE(ID) ON DELETE RESTRICT,
-- Название устройства, отображаемое в перечне трекеров у пользователя
  NAME TEXT,
-- Доменный ID
  TRACKER_ID TEXT UNIQUE NOT NULL,
-- Доменный ID текущего владельца
  ASSIGNEE TEXT,

  UNIQUE (DEVICE_ID, DEVICE_TYPE)
);


-- Aggregate Person ---------------------------------------


-- Таблица списка участников
CREATE TABLE PERSON(
-- Системный ID
  ID BIGSERIAL PRIMARY KEY,
-- Имя
  NAME TEXT NOT NULL,
-- Фамилия
  SURNAME TEXT NOT NULL,
-- Дата регистрации в системе
  REGDATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
-- Контактный email
  EMAIL TEXT,
-- Страна
  COUNTRY TEXT,
-- Доменный идентификатор
  PERSON_ID TEXT UNIQUE NOT NULL
);

-- Таблица назначенных трекеров
CREATE TABLE ASSIGNED_TRACKER(
  ID BIGINT REFERENCES PERSON(ID) ON DELETE CASCADE,
  -- Доменный идентификатор трекера
  TRACKER_ID TEXT NOT NULL,

  PRIMARY KEY (ID, TRACKER_ID)
);

-- Треки пилотов
CREATE TABLE PERSON_TRACKS(
  ID BIGINT REFERENCES PERSON(ID) ON DELETE CASCADE,
  -- Доменный идентификатор трека
  TRACK_ID TEXT NOT NULL,

  PRIMARY KEY (ID, TRACK_ID)
);


-- Aggregate Contest ------------------------------------

-- Таблица соревнования
CREATE TABLE CONTEST(
-- Системный ID
  ID BIGSERIAL PRIMARY KEY,
-- Предметный ID
  CONTEST_ID TEXT UNIQUE NOT NULL,
-- Название соревнования
  TITLE TEXT,
-- Дата и время начала
  START_TIME TIMESTAMPTZ,
-- Дата и время завершения
  END_TIME TIMESTAMPTZ,
  PLACE TEXT,
  COUNTRY TEXT,
  HQ_LAT REAL,
  HQ_LON REAL
);

-- Таблица участников соревнования
CREATE TABLE PARTICIPANT(
  ID BIGINT REFERENCES CONTEST(ID),
-- Доменный идентификатор участника
  PARTICIPANT_ID TEXT,
-- Роль на соревновании
  ROLE TEXT NOT NULL,
-- Параплан
  GLIDER TEXT,
-- Номер на соревновании
  CONTEST_NUMBER TEXT,
-- Описание
  DESCRIPTION TEXT,
  -- Тип участника (транспорт, человек)
  TYPE TEXT NOT NULL,

  PRIMARY KEY (ID, PARTICIPANT_ID)
);

-- Гонки соревнования
CREATE TABLE CONTEST_RACE(
  ID BIGINT REFERENCES CONTEST(ID),
  RACE_ID TEXT,

  PRIMARY KEY (RACE_ID, ID)
);


-- Aggregate Race --------------------------------------


CREATE TABLE RACE_TYPE(
  ID BIGSERIAL PRIMARY KEY,
  -- opendistance, racetogoal, speedrun etc.
  TYPE TEXT UNIQUE NOT NULL
);

-- Таблица со списком гонок
CREATE TABLE RACE(
-- Системный ID гонки
  ID BIGSERIAL PRIMARY KEY,
-- Доменный идентификатор
  RACE_ID TEXT UNIQUE NOT NULL,
-- Отображаемое название гонки
  TITLE TEXT,
-- Время начала - с учетом часового пояса
  START_TIME INTEGER NOT NULL,
-- Время начала соревнования
  MIN_START_TIME TIMESTAMPTZ NOT NULL,
-- Время начала - с учетом часового пояса
  END_TIME INTEGER NOT NULL,
-- Время окончания соревнования
  MAX_END_TIME TIMESTAMPTZ NOT NULL,
-- Тип гонки - из справочника RACE_TYPE
  RACE_TYPE BIGINT REFERENCES RACE_TYPE(ID),
-- Информация о чекпойнтах в гонке, в виде JSON
  CHECKPOINTS TEXT NOT NULL
);

-- Таблица парапланеристов
CREATE TABLE PARAGLIDER(
  -- Системный ID
  ID BIGINT REFERENCES RACE(ID) ON DELETE CASCADE ,
  -- Системный ID человека
  PERSON_ID TEXT NOT NULL,
  -- Постоянный номер на этом соревновании
  CONTEST_NUMBER TEXT,
  -- Страна участника
  COUNTRY TEXT NOT NULL ,
  GLIDER TEXT ,
  TRACKER_ID TEXT ,
  NAME TEXT NOT NULL ,
  SURNAME TEXT NOT NULL ,

  PRIMARY KEY (ID, PERSON_ID)
);

-- Треки в гонке
CREATE TABLE PARAGLIDER_TRACKS (
  ID BIGINT REFERENCES RACE (ID) ON DELETE CASCADE,
  -- Доменный идентификатор участника гонки
  PERSON_ID TEXT REFERENCES paraglider(PERSON_ID) ON DELETE CASCADE ,
  TRACK_ID TEXT UNIQUE,

  PRIMARY KEY (ID, PERSON_ID)
);


-- Aggregate Track -------------------------------------

-- Таблица типов треков
CREATE TABLE TRACK_TYPE(
  ID SERIAL PRIMARY KEY,
  NAME TEXT NOT NULL UNIQUE
);

insert into track_type (name) values('competition aftertask');

-- Таблица треков
CREATE TABLE TRACK(
	-- Системный ID трека
	ID BIGSERIAL PRIMARY KEY,
	-- Дата и время начала трека
	START_TIME INTEGER ,
	-- Дата и время окончания трека
	END_TIME INTEGER ,
  -- Доменный идентификатор трека,
	TRACK_ID TEXT UNIQUE NOT NULL,
	-- Тип трека
	TRACK_TYPE INT REFERENCES TRACK_TYPE(ID)
);

-- Данные треков
CREATE TABLE TRACK_DATA(
	ID BIGINT REFERENCES TRACK(ID) ON DELETE CASCADE ,
	TIMESTAMP INTEGER,
	LAT REAL,
	LON REAL,
	ALT SMALLINT ,
	G_SPEED REAL,
	V_SPEED REAL,
	DISTANCE REAL,

  PRIMARY KEY (TIMESTAMP, ID)
);

CREATE INDEX track_data_timestamp_idx
  ON track_data
  USING btree (timestamp);

-- Снимки состояний трека
CREATE TABLE TRACK_SNAPSHOT(
	ID BIGINT REFERENCES TRACK(ID),
	TIMESTAMP INTEGER ,
	SNAPSHOT TEXT NOT NULL,

  PRIMARY KEY (ID, TIMESTAMP)
);
