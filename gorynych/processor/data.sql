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
  TIMESTAMP TIMESTAMP NOT NULL,
  LAT REAL NOT NULL,
  LON REAL NOT NULL,
  -- Высота в метрах. 32767 метра более чем достаточно
  ALT SMALLINT NOT NULL,
  -- Скорость по земле в км/ч
  G_SPEED REAL,
  -- Вертикальная скорость м/с
  V_SPEED REAL,
  -- Дистанция в метрах
  DISTANCE INTEGER
) WITH (OIDS=FALSE);



-- Вставить данные в таблицу с треками.