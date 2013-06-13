-- Aggregate Person ---------------------------------------

CREATE TABLE PERSON(
  ID BIGSERIAL PRIMARY KEY,
  NAME TEXT NOT NULL,
  SURNAME TEXT NOT NULL,
  REGDATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  EMAIL TEXT UNIQUE,
  COUNTRY TEXT,
  PERSON_ID TEXT UNIQUE NOT NULL
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

-- select by_email
SELECT PERSON_ID FROM PERSON WHERE EMAIL=%s;