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

-- Select paragliders
SELECT * FROM PARAGLIDER WHERE ID=%s;

-- Insert paraglider
INSERT INTO PARAGLIDER VALUES (%s, %s, %s, %s, %s, %s, %s, %s);

-- Select race_id_by_organizator
SELECT
  r.race_id
FROM
  organizator o,
  race r
WHERE
  o.id = r.id
  AND o.person_id=%s
  AND (r.end_time BETWEEN %s AND %s or r.start_time BETWEEN %s AND %s);

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


-- Select cn_by_rid
SELECT p.contest_number
FROM
  paraglider p,
  race r
WHERE
  p.id = r.id AND
  p.tracker_id=%s;
