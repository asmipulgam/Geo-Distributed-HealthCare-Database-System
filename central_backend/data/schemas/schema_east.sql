-- Schema for 'west' database
USE east;

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
  PARTITION p_AL VALUES IN ('AL'),
  PARTITION p_CT VALUES IN ('CT'),
  PARTITION p_DE VALUES IN ('DE'),
  PARTITION p_FL VALUES IN ('FL'),
  PARTITION p_GA VALUES IN ('GA'),
  PARTITION p_MA VALUES IN ('MA'),
  PARTITION p_MD VALUES IN ('MD'),
  PARTITION p_ME VALUES IN ('ME'),
  PARTITION p_NC VALUES IN ('NC'),
  PARTITION p_NH VALUES IN ('NH'),
  PARTITION p_NJ VALUES IN ('NJ'),
  PARTITION p_NY VALUES IN ('NY'),
  PARTITION p_PA VALUES IN ('PA'),
  PARTITION p_RI VALUES IN ('RI'),
  PARTITION p_SC VALUES IN ('SC'),
  PARTITION p_VA VALUES IN ('VA'),
  PARTITION p_VT VALUES IN ('VT'),
  PARTITION p_WV VALUES IN ('WV')
);

CREATE TABLE IF NOT EXISTS outbox_events (
  "event_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "table_name" STRING NOT NULL,
  "op" STRING NOT NULL,
  "payload" JSONB NOT NULL,
  "created_at" TIMESTAMP DEFAULT now(),
  "processed" BOOLEAN DEFAULT false
);


