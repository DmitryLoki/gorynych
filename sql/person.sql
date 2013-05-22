-- Aggregate Person ---------------------------------------

CREATE TABLE PERSON(
  ID BIGSERIAL PRIMARY KEY,
  NAME TEXT NOT NULL,
  SURNAME TEXT NOT NULL,
  REGDATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  EMAIL TEXT,
  COUNTRY TEXT,
  PERSON_ID TEXT UNIQUE NOT NULL
);

CREATE TABLE ASSIGNED_TRACKER(
  ID BIGINT REFERENCES PERSON(ID) ON DELETE CASCADE,
  TRACKER_ID TEXT NOT NULL,

  PRIMARY KEY (ID, TRACKER_ID)
);

CREATE TABLE PERSON_TRACKS(
  ID BIGINT REFERENCES PERSON(ID) ON DELETE CASCADE,
  TRACK_ID TEXT NOT NULL,

  PRIMARY KEY (ID, TRACK_ID)
);

-- Insert Person
INSERT INTO PERSON(NAME, SURNAME, REGDATE, COUNTRY, EMAIL, PERSON_ID)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING ID;

-- Select Person
SELECT
  NAME, SURNAME, COUNTRY, EMAIL, REGDATE, PERSON_ID, ID
FROM
  PERSON
WHERE PERSON_ID=%s;

-- Update Person
UPDATE PERSON SET
  NAME=%s,
  SURNAME=%s,
  REGDATE=%s,
  COUNTRY=%s,
  EMAIL=%s
WHERE PERSON_ID = %s;