CREATE TABLE TRACKER_LAST_POINT(
  ID BIGINT REFERENCES TRACKER(ID) ON DELETE CASCADE PRIMARY KEY ,
  LAT REAL ,
  LON REAL ,
  ALT SMALLINT ,
  TIMESTAMP INTEGER
);


CREATE OR REPLACE FUNCTION add_to_last_point() RETURNS TRIGGER AS $$
        BEGIN
          INSERT INTO tracker_last_point (ID) VALUES (NEW.ID);
          RETURN NEW;
        END;
    $$ LANGUAGE plpgsql;

CREATE TRIGGER to_last_point
    AFTER INSERT ON tracker
    FOR EACH ROW EXECUTE PROCEDURE add_to_last_point();

insert into tracker_last_point (id) select id from tracker
