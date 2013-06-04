-- Event Store
CREATE TABLE IF NOT EXISTS events
    (
      EVENT_ID bigserial PRIMARY KEY,
      EVENT_NAME TEXT NOT NULL,
      AGGREGATE_ID TEXT NOT NULL,
      AGGREGATE_TYPE TEXT NOT NULL,
      EVENT_PAYLOAD BYTEA NOT NULL,
      OCCURED_ON TIMESTAMP NOT NULL
    );

CREATE TABLE IF NOT EXISTS dispatch (
  EVENT_ID bigint REFERENCES events(EVENT_ID) ON DELETE CASCADE,

  PRIMARY KEY (EVENT_ID)
);

CREATE OR REPLACE FUNCTION add_to_dispatch() RETURNS TRIGGER AS $$
        BEGIN
          INSERT INTO dispatch (EVENT_ID) VALUES (NEW.EVENT_ID);
          RETURN NEW;
        END;
    $$ LANGUAGE plpgsql;

CREATE TRIGGER to_dispatch
    AFTER INSERT ON events
    FOR EACH ROW EXECUTE PROCEDURE add_to_dispatch();