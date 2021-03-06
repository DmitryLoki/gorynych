-- Aggregate Race --------------------------------------

CREATE TABLE RACE_TYPE(
  ID BIGSERIAL PRIMARY KEY,
  -- opendistance, racetogoal, speedrun etc.
  TYPE TEXT UNIQUE NOT NULL
);
INSERT INTO RACE_TYPE(TYPE) VALUES ('racetogoal'), ('speedrun'),
('opendistance');

CREATE TABLE RACE(
  ID BIGSERIAL PRIMARY KEY,
  RACE_ID TEXT UNIQUE NOT NULL,
  TITLE TEXT,
  START_TIME INTEGER NOT NULL,
  END_TIME INTEGER NOT NULL,
  TIMEZONE TEXT NOT NULL ,
  RACE_TYPE BIGINT REFERENCES RACE_TYPE(ID),
  CHECKPOINTS TEXT NOT NULL,
  AUX_FIELDS TEXT,
  START_LIMIT_TIME INTEGER ,
  END_LIMIT_TIME INTEGER
);


CREATE TABLE PARAGLIDER(
  ID BIGINT REFERENCES RACE(ID) ON DELETE CASCADE ,
  PERSON_ID TEXT NOT NULL,
  CONTEST_NUMBER TEXT,
  COUNTRY TEXT NOT NULL ,
  GLIDER TEXT NOT NULL ,
  TRACKER_ID TEXT ,
  NAME TEXT NOT NULL ,
  SURNAME TEXT NOT NULL ,

  PRIMARY KEY (ID, PERSON_ID)
);


CREATE TABLE ORGANIZATOR(
  ID BIGINT REFERENCES RACE(ID) ON DELETE CASCADE ,
  PERSON_ID TEXT NOT NULL,
  DESCRIPTION TEXT ,
  TRACKER_ID TEXT ,

  PRIMARY KEY (ID, PERSON_ID)
);


CREATE TABLE RACE_TRANSPORT(
  ID BIGINT REFERENCES RACE(ID) ON DELETE CASCADE ,
  TRANSPORT_ID TEXT NOT NULL ,
  DESCRIPTION TEXT ,
  TITLE TEXT ,
  TRACKER_ID TEXT NOT NULL ,
  TYPE TEXT NOT NULL ,

  PRIMARY KEY (ID, TRANSPORT_ID)
);


-- Insert racetype
INSERT INTO RACE_TYPE(TYPE) VALUES (%s);

-- Insert race
INSERT INTO RACE(
  TITLE, START_TIME, END_TIME,
  TIMEZONE, RACE_TYPE, CHECKPOINTS, AUX_FIELDS, START_LIMIT_TIME,
  END_LIMIT_TIME, RACE_ID)
  VALUES (%s, %s, %s, %s, (
      SELECT ID FROM RACE_TYPE WHERE TYPE=%s), %s, %s, %s, %s, %s)
RETURNING ID;

-- Select race
SELECT
  ID, RACE_ID, TITLE, START_TIME, END_TIME, TIMEZONE, (SELECT TYPE FROM RACE_TYPE WHERE ID=RACE.RACE_TYPE), CHECKPOINTS, AUX_FIELDS, START_LIMIT_TIME, END_LIMIT_TIME
FROM RACE WHERE RACE_ID=%s;

-- Update race
UPDATE RACE SET (TITLE, START_TIME, END_TIME, TIMEZONE, RACE_TYPE,
                 CHECKPOINTS, AUX_FIELDS, START_LIMIT_TIME, END_LIMIT_TIME) =
  (%s, %s, %s, %s,  (
      SELECT ID FROM RACE_TYPE WHERE TYPE=%s), %s, %s, %s, %s)
WHERE RACE_ID=%s;


-- Select all_race
SELECT
  RACE_ID, ID, RACE_ID, TITLE, START_TIME, END_TIME, TIMEZONE, (SELECT TYPE FROM RACE_TYPE WHERE ID=RACE.RACE_TYPE), CHECKPOINTS, AUX_FIELDS, START_LIMIT_TIME, END_LIMIT_TIME
FROM RACE;


-- Select paragliders
SELECT * FROM PARAGLIDER WHERE ID=%s;

-- Insert paraglider
INSERT INTO PARAGLIDER VALUES (%s, %s, %s, %s, %s, %s, %s, %s);

-- Select current_race_by_tracker
SELECT
  r.race_id, p.contest_number
FROM
  race r,
  paraglider p
WHERE
  r.id = p.id AND
  p.tracker_id = (select tracker_id from tracker where device_id=%s) AND
  %s BETWEEN r.start_time AND r.end_time + 7*3600;


-- select transport
select * from race_transport where id=%s;


-- Select race_transport
SELECT
  TYPE, RACE_TRANSPORT.TITLE, DESCRIPTION, TRACKER_ID, TRANSPORT_ID
FROM
  RACE_TRANSPORT,
  RACE
WHERE
  RACE.RACE_ID=%s
  AND RACE.ID = RACE_TRANSPORT.ID;
