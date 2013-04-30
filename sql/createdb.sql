DROP SCHEMA IF EXISTS PUBLIC CASCADE;
CREATE SCHEMA PUBLIC;

-- Везде для тестов я создаю записи с ID = 0

-- Таблица типов устройств
CREATE TABLE DEVICE_TYPE(
	-- ID типу устройства
	DEVICE_TYPE_ID BIGSERIAL PRIMARY KEY,
	-- Наименование устройства
	NAME TEXT
);
-- Вносим тестовый тип
INSERT INTO DEVICE_TYPE (DEVICE_TYPE_ID, NAME)
VALUES (0, 'TEST TRACKER TYPE');
-- Таблица типов треков
CREATE TABLE TRACK_TYPE(
	ID BIGSERIAL PRIMARY KEY,
	NAME TEXT NOT NULL
);
INSERT INTO TRACK_TYPE(ID, NAME)
VALUES(0, 'TEST_NAME');
-- Таблица со списком трекеров
CREATE TABLE TRACKER(
	-- системный ID трекера 
	TID BIGSERIAL PRIMARY KEY,
	-- физический ID трекера (всякие IMEI и прочие уникальные коды устройства)
	DEVICE_ID TEXT,
	-- Тип устройства
	DEVICE_TYPE BIGINT REFERENCES DEVICE_TYPE(DEVICE_TYPE_ID),
	-- Название устройства, отображаемое в перечне трекеров у пользователя
	NAME TEXT,
	-- UUID трекера
	TRACKER_ID TEXT UNIQUE NOT NULL,
	-- На кого назначен
	ASSIGNEE TEXT
);
-- вносим тестовый трекер
INSERT INTO TRACKER (TID, DEVICE_ID, DEVICE_TYPE, NAME, TRACKER_ID, ASSIGNEE)
VALUES (0, 'TESTID0001', 0, 'TEST TRACKER', 'UUID-0000', NULL);
-- Таблица треков
CREATE TABLE TRACK(
	-- Системный ID трека
	ID BIGSERIAL PRIMARY KEY,
	-- Дата и время начала трека
	START_TIME TIMESTAMPTZ,
	-- Дата и время окончания трека
	END_TIME TIMESTAMPTZ,
	-- ID трекера, с которого получен этот трек
	TRACK_ID TEXT UNIQUE NOT NULL,
	-- Тип трека
	TRACK_TYPE BIGINT REFERENCES TRACK_TYPE(ID),
	-- ID трекера, с которого получен этот трек
	TRACKER_ID BIGINT REFERENCES TRACKER(TID)
);
INSERT INTO TRACK(ID, START_TIME, END_TIME, TRACK_ID, TRACK_TYPE, TRACKER_ID)
VALUES (0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'UUID-0000', 0, 0);
-- Таблица списка участников
CREATE TABLE PERSON(
	-- Системный ID
	ID BIGSERIAL PRIMARY KEY,
	-- Имя
	FIRSTNAME TEXT,
	-- Фамилия
	LASTNAME TEXT NOT NULL,
	-- Дата регистрации в системе
	REGDATE TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
	-- Контактный email
	EMAIL TEXT,
	-- Страна
	COUNTRY TEXT,
	-- UUID
	PERSON_ID TEXT UNIQUE NOT NULL
);
ALTER TABLE PERSON OWNER TO AIRTRIBUNE;
-- Тестовый участник
INSERT INTO PERSON(ID, FIRSTNAME, LASTNAME, REGDATE, EMAIL, COUNTRY, PERSON_ID)
VALUES (0, 'TEST_FIRSTNAME', 'TEST_LASTNAME', CURRENT_TIMESTAMP, 'TEST@TEST.COM', 'TEST_COUNTRY', '1c486eaf-03eb-49d2-a553-b28b985e6546');
-- Таблица личных данных
CREATE TABLE PERSON_DATA(
	-- ID человека
	ID BIGINT REFERENCES PERSON(ID),
	-- Тип записи
	DATA_TYPE TEXT,
	-- Содержимое записи
	DATA_VALUE TEXT,
	-- Отображать?
	VISIBLE BOOLEAN,
	-- С какой по какую дату актуальна запись
	EFFECTIVE INTERVAL
);
-- Добавляем тестовую строку
INSERT INTO PERSON_DATA(ID, DATA_TYPE, DATA_VALUE)
VALUES (0, 'facebook', 'http://www.facebook.com/testuser');
-- Таблица назначенных трекеров
CREATE TABLE ASSIGNED_TRACKER(
	PERSON_ID BIGINT REFERENCES PERSON(ID),
	TRACKER_ID BIGINT REFERENCES TRACKER(TID),
	ASSIGNED TIMESTAMPTZ,
	TAKEN_BACK TIMESTAMPTZ
);
INSERT INTO ASSIGNED_TRACKER(PERSON_ID, TRACKER_ID, ASSIGNED)
VALUES (0, 0, CURRENT_TIMESTAMP);
-- Треки пилотов
CREATE TABLE PERSON_TRACKS(
	PID BIGINT REFERENCES PERSON(ID),
	TRACK_ID BIGINT REFERENCES TRACK(ID)
);
INSERT INTO PERSON_TRACKS(PID, TRACK_ID)
VALUES (0, 0);
-- Данные треков
CREATE TABLE TRACK_DATA(
	TRID BIGINT REFERENCES TRACK(ID),
	TS TIMESTAMP,
	LAT REAL,
	LON REAL,
	ALT REAL,
	G_SPEED REAL,
	V_SPEED REAL,
	DISTANCE REAL
);
CREATE TABLE TRACK_SNAPSHOT(
	TRID BIGINT REFERENCES TRACK(ID),
	TS TIMESTAMP,
	SNAPSHOT TEXT
);
CREATE TABLE RACE_TYPE(
	ID BIGSERIAL PRIMARY KEY,
	TYPE TEXT UNIQUE NOT NULL
);
INSERT INTO RACE_TYPE(ID, TYPE)
VALUES(0, 'TEST TYPE');
-- Таблица со списком гонок
CREATE TABLE RACE(
	-- Системный ID гонки
	ID BIGSERIAL PRIMARY KEY,
	-- UUID
	RACE_ID TEXT UNIQUE NOT NULL,
	-- Отображаемое название гонки
	TITLE TEXT NOT NULL,
	-- Время начала - с учетом часового пояса
	START_TIME TIMESTAMPTZ NOT NULL,
	-- Время начала - с учетом часового пояса
	MIN_START_TIME TIMESTAMPTZ NOT NULL,
	-- Время начала - с учетом часового пояса
	END_TIME TIMESTAMPTZ NOT NULL,
	-- Время окончания - с учетом часового пояса
	MAX_END_TIME TIMESTAMPTZ NOT NULL,
	-- Тип гонки - из справочника RACE_TYPE
	RACE_TYPE BIGINT REFERENCES RACE_TYPE(ID),
	-- Информация о чекпойнтах в гонке, в виде JSON
	CHECKPOINTS TEXT
);
-- Добавляем тестовую гонку
INSERT INTO RACE(ID, RACE_ID, TITLE, START_TIME, END_TIME, MIN_START_TIME, MAX_END_TIME, RACE_TYPE)
VALUES (0, 'UUID-0000', 'TEST RACE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0);
-- Таблица со списком чекпойнтов на гонку
CREATE TABLE CHECKPOINT(
	-- Системный ID чекпойнта
	CHECKPOINT_ID BIGSERIAL PRIMARY KEY,
	-- Гонка, к которой он относится
	RACE_ID BIGINT REFERENCES RACE(ID),
	-- Каким по порядку он должен быть пройден
	NUM INT NOT NULL,
	-- Название чекпойнта
	NAME TEXT NOT NULL,
	-- Геометрия чекпойнта (тут вопрос, в каком формате)
	GEOMETRY TEXT,
	-- Тип чекпойнта (Старт, финиш, еще что-нибудь)
	TYPE TEXT NOT NULL,
	-- Время открытия (не факт что нужно, т.к. по идее - свойство гонки)
	TIMES TIMESTAMPTZ
);
-- Добавляем тестовый чекпойнт
INSERT INTO CHECKPOINT(CHECKPOINT_ID, RACE_ID, NUM, NAME, GEOMETRY, TYPE, TIMES)
VALUES (0, 0, 1, 'TEST START', 'TEST GEOMETRY', 'START', CURRENT_TIMESTAMP);
-- Таблица с адресами штаб-кварир конкретной гонки
CREATE TABLE HQ_ADDRESS(
	-- Системный ID
	HQ_ID BIGSERIAL PRIMARY KEY,
	-- Страна
	COUNTRY TEXT,
	-- Область, район
	DISTRICT TEXT,
	-- Населенный пункт
	CITY TEXT,
	-- Адрес
	ADDRESS TEXT,
	-- Точные координаты штаб-квартиры
	LAT REAL,
	LON REAL
);
-- Добавляем тестовый адрес
INSERT INTO HQ_ADDRESS(HQ_ID, COUNTRY, DISTRICT, CITY, ADDRESS, LAT, LON)
VALUES (0, 'TEST_COUNTRY', 'TEST DISTRICT', 'TEST CITY', 'TEST ADDRESS', 10, 10);
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
-- Добавляем геометрическую координату
-- SELECT AddGeometryColumn ('public','contest','hq_coord',4326,'POINT',2);
-- Тестовое соревнование
INSERT INTO CONTEST(ID, CONTEST_ID, TITLE, START_TIME, END_TIME, PLACE, COUNTRY, HQ_LAT, HQ_LON)
VALUES (0, 'cnts-130430-677825258', 'TEST CONTEST', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'TEST_PLACE', 'TEST_COUNTRY', 10.0, 20.0);
-- Таблица парапланов
CREATE TABLE PARAGLIDER(
	ID BIGSERIAL PRIMARY KEY,
	-- Системный ID параплана
	RID BIGINT REFERENCES RACE(ID),
	-- Системный ID человека
	PERSON_ID TEXT REFERENCES PERSON(PERSON_ID),
	-- Постоянный номер на этом соревновании
	CONTEST_NUMBER TEXT,
	-- Страна участника
	COUNTRY TEXT,
	GLIDER TEXT,
	TRACKER_ID TEXT REFERENCES TRACKER(TRACKER_ID),
	NAME TEXT
);
INSERT INTO PARAGLIDER(ID, RID, PERSON_ID, CONTEST_NUMBER, COUNTRY, GLIDER, TRACKER_ID, NAME)
VALUES (0, 0, '1c486eaf-03eb-49d2-a553-b28b985e6546', 'cnts-130430-677825258', 'TEST_COUNTRY', 'TEST_GLIDER', 'UUID-0000', 'TEST_NAME');
-- Таблица организаторов
CREATE TABLE ORGANIZATOR(
	-- ID человека
	PERSON_ID BIGINT REFERENCES PERSON(ID),
	-- ID соревнования
	CONTEST_ID BIGINT REFERENCES CONTEST(ID),
	-- Роль человека на соревновании
	ROLE TEXT
);
-- Тестовый организатор
INSERT INTO ORGANIZATOR(PERSON_ID, CONTEST_ID, ROLE)
VALUES (0, 0, 'org');
-- Таблица участников соревнования
CREATE TABLE PARTICIPANT(
	CID BIGINT REFERENCES CONTEST(ID),
	-- UUID из таблицы PERSON
	PARTICIPANT_ID TEXT,
	-- Роль на соревновании
	ROLE TEXT,
	-- Параплан
	GLIDER TEXT,
	-- Номер на соревновании
	CONTEST_NUMBER TEXT,
	-- Описание
	DESCRIPTION TEXT
);
-- Тестовый участник
INSERT INTO PARTICIPANT(CID, PARTICIPANT_ID, ROLE, GLIDER, CONTEST_NUMBER, DESCRIPTION)
VALUES (0, '1c486eaf-03eb-49d2-a553-b28b985e6546', 'paraglider', 'niviuk', 'cnts-130430-677825258', 'TEST DESCRIPTION');
-- Таблица транспорта
CREATE TABLE TRANSPORT(
	TRANSPORT_ID BIGSERIAL PRIMARY KEY,
	TRANSPORT_TYPE TEXT,
	TITLE TEXT,
	DESCRIPTION TEXT,
	ASSIGNED_TRACKER BIGINT
);
-- TODO