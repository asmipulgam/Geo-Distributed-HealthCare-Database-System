-- Schema for 'west' database
-- CREATE DATABASE IF NOT EXISTS central;
-- USE central;

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
  PARTITION p_AR VALUES IN ('AR'),
  PARTITION p_IA VALUES IN ('IA'),
  PARTITION p_IL VALUES IN ('IL'),
  PARTITION p_IN VALUES IN ('IN'),
  PARTITION p_KS VALUES IN ('KS'),
  PARTITION p_KY VALUES IN ('KY'),
  PARTITION p_LA VALUES IN ('LA'),
  PARTITION p_MI VALUES IN ('MI'),
  PARTITION p_MN VALUES IN ('MN'),
  PARTITION p_MO VALUES IN ('MO'),
  PARTITION p_MS VALUES IN ('MS'),
  PARTITION p_ND VALUES IN ('ND'),
  PARTITION p_NE VALUES IN ('NE'),
  PARTITION p_OH VALUES IN ('OH'),
  PARTITION p_OK VALUES IN ('OK'),
  PARTITION p_SD VALUES IN ('SD'),
  PARTITION p_TN VALUES IN ('TN'),
  PARTITION p_TX VALUES IN ('TX'),
  PARTITION p_WI VALUES IN ('WI')
);

CREATE TABLE IF NOT EXISTS outbox_events (
  "event_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "table_name" STRING NOT NULL,
  "op" STRING NOT NULL,
  "payload" JSONB NOT NULL,
  "created_at" TIMESTAMP DEFAULT now(),
  "processed" BOOLEAN DEFAULT false
);
