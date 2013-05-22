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

-- Добавляем событие.
INSERT INTO events
(EVENT_NAME, AGGREGATE_ID, AGGREGATE_TYPE, EVENT_PAYLOAD, OCCURED_ON)
VALUES (%s, %s, %s, %s, %s);

-- Select events.
SELECT * FROM events
  WHERE AGGREGATE_ID = %s
  ORDER BY EVENT_ID;

-- Выбрать из таблицы события определённых типов, которые ещё не были обработаны.
SELECT e.aggregate_id, e.event_payload
FROM events e, dispatch d
WHERE (event_name = 'RaceCheckpointsChanged' OR event_name = 'ParagliderRegisteredOnContest') AND e.event_id = d.event_id;