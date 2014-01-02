-- Aggregate Transport -----------------------------------------
CREATE TABLE TRANSPORT_TYPE(
  ID SERIAL PRIMARY KEY ,
  TRANSPORT_TYPE TEXT UNIQUE NOT NULL
);

INSERT INTO TRANSPORT_TYPE(TRANSPORT_TYPE) VALUES ('bus'), ('car'),
('motorcycle'), ('helicopter');

CREATE TABLE TRANSPORT(
  ID BIGSERIAL PRIMARY KEY ,
  TRANSPORT_ID TEXT UNIQUE NOT NULL ,
  TITLE TEXT NOT NULL ,
  TYPE INT REFERENCES TRANSPORT_TYPE(ID) NOT NULL ,
  DESCRIPTION TEXT,
  PHONE CHARACTER VARYING(50)
);

-- Select transport
SELECT
  ID, TRANSPORT_ID, TITLE,
  (SELECT TRANSPORT_TYPE FROM TRANSPORT_TYPE WHERE ID=TYPE),
  DESCRIPTION, PHONE
FROM TRANSPORT
WHERE
  TRANSPORT_ID = %s;

-- Select all_transport
SELECT
  TRANSPORT_ID, ID, TRANSPORT_ID, TITLE,
  (SELECT TRANSPORT_TYPE FROM TRANSPORT_TYPE WHERE ID=TYPE),
  DESCRIPTION, PHONE
FROM TRANSPORT;

-- Insert transport
INSERT INTO TRANSPORT(TITLE, TYPE, DESCRIPTION, PHONE, TRANSPORT_ID)
    VALUES (%s,
            (SELECT ID FROM TRANSPORT_TYPE WHERE TRANSPORT_TYPE=%s),
            %s, %s, %s)
RETURNING ID;


-- Update transport
UPDATE TRANSPORT SET
  TITLE=%s,
  TYPE=(SELECT ID FROM TRANSPORT_TYPE WHERE TRANSPORT_TYPE=%s),
  DESCRIPTION=%s,
  PHONE=%s
WHERE TRANSPORT_ID=%s;

-- Select transport_for_contest
SELECT
  transport_type.transport_type,
  transport.title,
  transport.description,
  tracker.tracker_id,
  transport.transport_id
FROM
  contest,
  participant,
  tracker,
  tracker_assignees,
  transport,
  transport_type
WHERE
  participant.participant_id = transport.transport_id AND
  participant.id = contest.id AND
  tracker.id = tracker_assignees.id AND
  tracker_assignees.assignee_id = participant.participant_id AND
  transport.type = transport_type.id AND
  participant.type = 'transport' AND
  contest.contest_id = %s;

