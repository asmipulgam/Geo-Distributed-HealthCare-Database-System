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