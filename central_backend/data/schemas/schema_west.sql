-- Schema for 'west' database
-- CREATE DATABASE IF NOT EXISTS west;
-- USE west;

CREATE TABLE IF NOT EXISTS patients (
  "id" INT,
  "first_name" STRING,
  "last_name" STRING,
  "email" STRING,
  "Phone number" STRING,
  "weight" DECIMAL(6,2),
  "age" INT,
  "gender" STRING,
  "Prefix" STRING,
  "Martial Status" STRING,
  "Address" STRING,
  "City" STRING,
  "State" STRING,
  "Hospital Name" STRING,
  "Hospital Address" STRING,
  "Region" STRING,
  "Visit Date" DATE,
  "Treatment" STRING,
  "Doctor Appointed" STRING,
  "Number of Doctors Appointed" INT,
  "Doctor's Contact" STRING,
  "Allergies" STRING,
  "Height" DECIMAL(5,2),
  PRIMARY KEY ("State","id")
) PARTITION BY LIST ("State") (
  PARTITION p_AK VALUES IN ('AK'),
  PARTITION p_AZ VALUES IN ('AZ'),
  PARTITION p_CA VALUES IN ('CA'),
  PARTITION p_CO VALUES IN ('CO'),
  PARTITION p_HI VALUES IN ('HI'),
  PARTITION p_ID VALUES IN ('ID'),
  PARTITION p_MT VALUES IN ('MT'),
  PARTITION p_NM VALUES IN ('NM'),
  PARTITION p_NV VALUES IN ('NV'),
  PARTITION p_OR VALUES IN ('OR'),
  PARTITION p_UT VALUES IN ('UT'),
  PARTITION p_WA VALUES IN ('WA'),
  PARTITION p_WY VALUES IN ('WY')
);

CREATE TABLE IF NOT EXISTS outbox_events (
  "event_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "table_name" STRING NOT NULL,
  "op" STRING NOT NULL,
  "payload" JSONB NOT NULL,
  "created_at" TIMESTAMP DEFAULT now(),
  "processed" BOOLEAN DEFAULT false
);

-- CockroachDB does not support the PostgreSQL "CREATE ... PARTITION OF" child
-- table syntax. Use a PARTITION BY LIST clause instead (via ALTER TABLE or
-- inline CREATE). Below we declare partitions using ALTER TABLE which is
-- compatible with CockroachDB's partitioning model.
