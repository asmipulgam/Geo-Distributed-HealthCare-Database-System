CREATE TABLE IF NOT EXISTS doctors (
  "Doctor_ID" STRING PRIMARY KEY,
  "Doctor_Name" STRING,
  "Hospital" STRING,
  "Region" STRING
);


CREATE TABLE IF NOT EXISTS patients_central (
  "Patient_ID" STRING,
  "Patient_Name" STRING,
  "Doctor_ID" STRING,
  "Doctor_Name" STRING,
  "Age" INT,
  "Gender" STRING,
  "Phone" STRING,
  "Email" STRING,
  "Address" STRING,
  "State" STRING,
  "Region" STRING,
  "Appointment_Date" DATE,
  "Diagnosis" STRING,
  "Date_of_Birth" DATE,
  "is_organ_donor" BOOLEAN,
  "lat" FLOAT8,
  "lon" FLOAT8,
  PRIMARY KEY ("State","Patient_ID"),
  FOREIGN KEY ("Doctor_ID") REFERENCES doctors("Doctor_ID")
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

CREATE TABLE IF NOT EXISTS patients_west (
  "Patient_ID" STRING,
  "Patient_Name" STRING,
  "Doctor_ID" STRING,
  "Doctor_Name" STRING,
  "Age" INT,
  "Gender" STRING,
  "Phone" STRING,
  "Email" STRING,
  "Address" STRING,
  "State" STRING,
  "Region" STRING,
  "Appointment_Date" DATE,
  "Diagnosis" STRING,
  "Date_of_Birth" DATE,
  "is_organ_donor" BOOLEAN,
  "lat" FLOAT8,
  "lon" FLOAT8,
  PRIMARY KEY ("State","Patient_ID"),
  FOREIGN KEY ("Doctor_ID") REFERENCES doctors("Doctor_ID")
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


CREATE OR REPLACE FUNCTION haversine_km(
  lat1 float8, lon1 float8, lat2 float8, lon2 float8
)
RETURNS float8
RETURNS NULL ON NULL INPUT
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT (2.0::float8 * 6371.0088::float8) * ASIN(
    SQRT(
      POWER(SIN(RADIANS(lat2 - lat1) / 2.0), 2.0) +
      COS(RADIANS(lat1)) * COS(RADIANS(lat2)) *
      POWER(SIN(RADIANS(lon2 - lon1) / 2.0), 2.0)
    )
  );
$$;
