-- Schema for 'west' database
USE west;

CREATE TABLE IF NOT EXISTS patients (
  "id" INT PRIMARY KEY,
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
  "Hostipal Address" STRING,
  "Region" STRING,
  "Visit Date" DATE,
  "Treatement" STRING,
  "Doctor Appointed" STRING,
  "Number of Doctors Appointed" INT,
  "Doctor's Contact" STRING,
  "Allergies" STRING,
  "Height" DECIMAL(5,2)
);

CREATE TABLE IF NOT EXISTS outbox_events (
  "event_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "table_name" STRING NOT NULL,
  "op" STRING NOT NULL,
  "payload" JSONB NOT NULL,
  "created_at" TIMESTAMP DEFAULT now(),
  "processed" BOOLEAN DEFAULT false
);
