CREATE TABLE IF NOT EXISTS events
(
  -- Сквозной номер события, нужен для publishing события в queue.
  EVENT_ID bigserial PRIMARY KEY,
  -- Имя события (имя класса).
  EVENT_NAME TEXT NOT NULL,
  -- Идентификатор агрегата
  AGGREGATE_ID TEXT NOT NULL,
  -- тип агрегата
  AGGREGATE_TYPE TEXT NOT NULL,
  -- Содержимое события.
  EVENT_PAYLOAD BYTEA NOT NULL,
  -- Временная метка события.
  OCCURED_ON TIMESTAMP NOT NULL

);

-- Функция, добавляющая идентификатор события в таблицу dispatch после
-- сохранения события в events.
CREATE OR REPLACE FUNCTION add_to_dispatch() RETURNS TRIGGER AS $$
    BEGIN
      INSERT INTO dispatch (EVENT_ID) VALUES (NEW.EVENT_ID);
      RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

-- Добавление триггера к events
CREATE TRIGGER to_dispatch
AFTER INSERT ON events
FOR EACH ROW EXECUTE PROCEDURE add_to_dispatch();

-- Таблица, в которой хранятся идентификаторы неопубликованных событий.
CREATE TABLE IF NOT EXISTS dispatch (
  -- Идентификатор события
  EVENT_ID bigint NOT NULL

);

CREATE TABLE IF NOT EXISTS streams (
  -- stream system id
  ID bigserial PRIMARY KEY,
  -- тип агрегата он же имя потока
  AGGREGATE_TYPE TEXT NOT NULL,
  -- идентификатор агрегата он же доменный идентификатор потока
  AGGREGATE_ID TEXT NOT NULL UNIQUE,

  UNIQUE (AGGREGATE_ID, AGGREGATE_TYPE)

);

-- Шаг 0: при создании нового потока добавить его в streams.
INSERT INTO streams (AGGREGATE_ID, AGGREGATE_TYPE) VALUES (%s, %s);

-- Шаг 2: добавляем событие.
INSERT INTO events
(EVENT_NAME, AGGREGATE_ID, AGGREGATE_TYPE, EVENT_PAYLOAD, OCCURED_ON)
VALUES (%s, %s, %s, %s, %s);

-- Select event stream.
SELECT * FROM events
  WHERE AGGREGATE_ID = %s
  ORDER BY EVENT_ID;
