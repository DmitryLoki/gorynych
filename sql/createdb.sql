DROP SCHEMA IF EXISTS AIRTRIBUNE_TEST CASCADE;
CREATE SCHEMA AIRTRIBUNE_TEST;
SET SEARCH_PATH TO AIRTRIBUNE_TEST, PUBLIC;

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

-- Таблица со списком трекеров
CREATE TABLE TRACKER(
	-- системный ID трекера 
	TRACKER_ID BIGSERIAL PRIMARY KEY,
	-- физический ID трекера (всякие IMEI и прочие уникальные коды устройства)
	DEVICE_ID TEXT,
	-- Тип устройства
	DEVICE_TYPE BIGINT REFERENCES DEVICE_TYPE(DEVICE_TYPE_ID),
	-- Название устройства, отображаемое в перечне трекеров у пользователя
	NAME TEXT
);
-- вносим тестовый трекер
INSERT INTO TRACKER (TRACKER_ID, DEVICE_ID, DEVICE_TYPE, NAME)
VALUES (0, 'TESTID0001', 0, 'TEST TRACKER');

-- Справочник стран
CREATE TABLE COUNTRY(
	-- Системный ID страны
	COUNTRY_ID BIGSERIAL PRIMARY KEY,
	-- Код страны по справочнику.
	COUNTRY_CODE TEXT,
	-- Название страны, отображаемое на клиенте
	NAME TEXT
);
-- Вносим тестовую страну
INSERT INTO COUNTRY(COUNTRY_ID, COUNTRY_CODE, NAME)
VALUES (0, 'TEST', 'TEST COUNTRY');

-- Таблица со списком гонок
CREATE TABLE RACE(
	-- Системный ID гонки
	RACE_ID BIGSERIAL PRIMARY KEY,
	-- Отображаемое название гонки
	TITLE TEXT NOT NULL,
	-- Время начала - с учетом часового пояса
	START_TIME TIMESTAMPTZ NOT NULL,
	-- Время окончания - с учетом часового пояса
	FINISH_TIME TIMESTAMPTZ NOT NULL
);

-- Добавляем тестовую гонку
INSERT INTO RACE(RACE_ID, TITLE, START_TIME, FINISH_TIME)
VALUES (0, 'TEST RACE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Таблица со списком чекпойнтов на гонку
CREATE TABLE CHECKPOINT(
	-- Системный ID чекпойнта
	CHECKPOINT_ID BIGSERIAL PRIMARY KEY,
	-- Гонка, к которой он относится
	RACE_ID BIGINT REFERENCES RACE(RACE_ID),
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
	COUNTRY BIGINT REFERENCES COUNTRY(COUNTRY_ID),
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
VALUES (0, 0, 'TEST DISTRICT', 'TEST CITY', 'TEST ADDRESS', 10, 10);

-- Таблица соревнования
CREATE TABLE CONTEST(
	-- Системный ID 
	CONTEST_ID BIGSERIAL PRIMARY KEY,
	-- Название соревнования
	TITLE TEXT,
	-- Дата и время начала
	START_DATE TIMESTAMPTZ,
	-- Дата и время завершения
	END_DATE TIMESTAMPTZ,
	-- Ссылка на HQ
	HQ BIGINT REFERENCES HQ_ADDRESS(HQ_ID)
);

-- Тестовое соревнование
INSERT INTO CONTEST(CONTEST_ID, TITLE, START_DATE, END_DATE, HQ)
VALUES (0, 'TEST CONTEST', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0);

-- Таблица списка участников
CREATE TABLE PERSON(
	-- Системный ID
	PERSON_ID BIGSERIAL PRIMARY KEY,
	-- Фамилия
	LASTNAME TEXT NOT NULL,
	-- Имя
	FIRSTNAME TEXT,
	-- Дата регистрации в системе
	REGDATE TIMESTAMPTZ,
	-- Контактный email
	EMAIL TEXT
);

-- Тестовый участник
INSERT INTO PERSON(PERSON_ID, LASTNAME, FIRSTNAME, REGDATE, EMAIL)
VALUES (0, 'TEST_LASTNAME', 'TEST_FIRSTNAME', CURRENT_TIMESTAMP, 'TEST@TEST.COM');

-- Таблица организаторов
CREATE TABLE ORGANIZATOR(
	-- ID человека
	PERSON_ID BIGINT REFERENCES PERSON(PERSON_ID),
	-- ID соревнования
	CONTEST_ID BIGINT REFERENCES CONTEST(CONTEST_ID),
	-- Роль человека на соревновании
	ROLE TEXT
);

-- Тестовый организатор
INSERT INTO ORGANIZATOR(PERSON_ID, CONTEST_ID, ROLE)
VALUES (0, 0, 'org');

-- Таблица участников соревнования
CREATE TABLE PARTICIPANT(
	CONTEST_ID BIGINT REFERENCES CONTEST(CONTEST_ID),
	PERSON_ID BIGINT REFERENCES PERSON(PERSON_ID),
	-- Роль на соревновании
	ROLE TEXT
);

-- Тестовый участник
INSERT INTO PARTICIPANTS(CONTEST_ID, PERSON_ID, ROLE)
VALUES (0, 0, 'PILOT');

-- Таблица парапланов
CREATE TABLE PARAGLIDER(
	-- Системный ID параплана
	GLIDER_ID BIGSERIAL PRIMARY KEY,
	-- Системный ID человека
	PERSON_ID BIGINT REFERENCES PERSON(PERSON_ID),
	-- Постоянный номер на этом соревновании
	CONTEST_NUMBER BIGINT,
	-- Страна участника
	COUNTRY BIGINT REFERENCES COUNTRY(COUNTRY_ID)
);

INSERT INTO PARAGLIDER(GLIDER_ID, PERSON_ID, CONTEST_NUMBER, COUNTRY)
VALUES (0, 0, 0, 0);

-- Таблица назначенных трекеров
CREATE TABLE ASSIGNED_TRACKER(
	PERSON_ID BIGINT REFERENCES PERSON(PERSON_ID),
	TRACKER_ID BIGINT REFERENCES TRACKER(TRACKER_ID),
	ASSIGNED TIMESTAMPTZ,
	TAKEN_BACK TIMESTAMPTZ
);

INSERT INTO ASSIGNED_TRACKER(PERSON_ID, TRACKER_ID, ASSIGNED)
VALUES (0, 0, CURRENT_TIMESTAMP);
-- TODO