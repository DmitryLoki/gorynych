-- Aggregate Track -------------------------------------

CREATE TABLE TRACK_TYPE(
  ID SERIAL PRIMARY KEY,
  NAME TEXT NOT NULL UNIQUE
);

insert into track_type (name) values('competition_aftertask');

CREATE TABLE TRACK(
	ID SERIAL PRIMARY KEY,
	START_TIME INTEGER ,
	END_TIME INTEGER ,
	TRACK_ID TEXT UNIQUE NOT NULL,
	TRACK_TYPE INT REFERENCES TRACK_TYPE(ID) ON DELETE CASCADE
);

CREATE TABLE TRACK_DATA(
	ID INT REFERENCES TRACK(ID) ON DELETE CASCADE ,
	TIMESTAMP INTEGER,
	LAT REAL,
	LON REAL,
	ALT SMALLINT ,
	G_SPEED REAL,
	V_SPEED REAL,
	DISTANCE INTEGER ,

  PRIMARY KEY (TIMESTAMP, ID)
);

CREATE INDEX track_data_timestamp_idx
  ON track_data
  USING btree (timestamp);

CREATE TABLE TRACK_SNAPSHOT(
  ID INT REFERENCES TRACK(ID) ON DELETE CASCADE ,
	TIMESTAMP INTEGER ,
	SNAPSHOT TEXT NOT NULL,

  PRIMARY KEY (ID, TIMESTAMP)
);

CREATE TABLE TRACKS_GROUP(
  GROUP_ID TEXT ,
  TRACK_ID INT REFERENCES TRACK(ID) ON DELETE CASCADE ,
  TRACK_LABEL TEXT,

  PRIMARY KEY (GROUP_ID, TRACK_ID)
);


-- Select track
SELECT track_id from track where track_id=%s;


-- Select tracks
SELECT
  track_type.name,
  track.track_id,
  track.start_time,
  track.end_time
FROM
  track_type,
  tracks_group,
  track
WHERE
  tracks_group.track_id = track.id AND
  tracks_group.group_id = %s;


-- Select track_for_contest_number
SELECT
  track_type.name,
  track.track_id,
  track.start_time,
  track.end_time,
  tracks_group.track_label
FROM
    track_type,
    tracks_group,
    track
WHERE
  tracks_group.track_id = track.id AND
  tracks_group.group_id = %s AND
  TRACKS_GROUP.TRACK_LABEL = %s;
