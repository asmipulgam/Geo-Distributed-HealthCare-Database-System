from faker import Faker
import csv
import random

fake = Faker('en_US')

# ----------------------------
# CONFIGURATION
# ----------------------------
NUM_DOCTORS = 30000
PATIENTS_PER_REGION = 90000
REGIONS = ["West", "Central"]  # Only West & Central

# Define rough coordinate ranges for regions (approximate USA ranges)
REGION_COORDS = {
    "West": {
        "lat_min": 32.0, "lat_max": 49.0,   # California to Washington
        "lon_min": -124.5, "lon_max": -112.0
    },
    "Central": {
        "lat_min": 29.0, "lat_max": 48.0,   # Texas to Minnesota
        "lon_min": -105.0, "lon_max": -90.0
    }
}

# ----------------------------
# STEP 1: Generate Doctor Table (West + Central)
# ----------------------------
def generate_doctors(num_doctors):
    doctors = []
    used_ids = set()

    while len(doctors) < num_doctors:
        doctor_id = f"DR-{random.randint(100000, 999999)}"
        if doctor_id in used_ids:
            continue
        used_ids.add(doctor_id)
        region = random.choice(["West", "Central"])
        doctors.append({
            "Doctor_ID": doctor_id,
            "Doctor_Name": fake.name(),
            "Hospital": fake.company(),
            "Region": region
        })
    return doctors


def save_doctors_csv(doctors):
    with open("Doctors.csv", "w", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Doctor_ID", "Doctor_Name", "Hospital", "Region"])
        for d in doctors:
            writer.writerow([d["Doctor_ID"], d["Doctor_Name"], d["Hospital"], d["Region"]])
    print(f"✅ {len(doctors)} doctor records written → Doctors.csv")


# ----------------------------
# STEP 2: Generate Patient Tables + Locations
# ----------------------------
def generate_patients(region, doctors, count):
    patient_file = f"Patients_{region.upper()}.csv"
    location_file = f"Patient_Location_{region.upper()}.csv"

    with open(patient_file, "w", newline="", encoding="utf-8") as pf, \
         open(location_file, "w", newline="", encoding="utf-8") as lf:
        
        patient_writer = csv.writer(pf)
        location_writer = csv.writer(lf)

        # Headers (Phone removed)
        patient_writer.writerow([
            "Patient_ID", "Patient_Name", "Doctor_ID", "Doctor_Name",
            "Age", "Gender", "Email", "Address",
            "Region", "Appointment_Date", "Diagnosis", "Date_of_Birth", "Organ_Donor"
        ])
        location_writer.writerow(["Patient_ID", "Latitude", "Longitude"])

        region_doctors = [d for d in doctors if d["Region"] == region]

        used_patient_ids = set()

        while len(used_patient_ids) < count:
            patient_id = f"PT-{random.randint(100000, 999999)}"
            if patient_id in used_patient_ids:
                continue
            used_patient_ids.add(patient_id)

            doctor = random.choice(region_doctors)

            age = random.randint(18, 90)
            gender = random.choice(["Male", "Female", "Other"])
            dob = fake.date_of_birth(minimum_age=age, maximum_age=age).strftime("%Y-%m-%d")
            organ_donor = random.choice(["Yes", "No"])
            address = fake.address().replace("\n", ", ")

            # Write patient record
            patient_writer.writerow([
                patient_id,
                fake.name(),
                doctor["Doctor_ID"],
                doctor["Doctor_Name"],
                age,
                gender,
                fake.email(),
                address,
                region,
                fake.date_between(start_date='-2y', end_date='today'),
                random.choice([
                    "Diabetes", "Hypertension", "Flu", "Asthma", "Back Pain",
                    "Covid-19", "Allergy", "Migraine", "Anxiety", "Arthritis"
                ]),
                dob,
                organ_donor
            ])

            # Generate coordinates only for organ donors
            if organ_donor == "Yes":
                lat = round(random.uniform(REGION_COORDS[region]["lat_min"], REGION_COORDS[region]["lat_max"]), 5)
                lon = round(random.uniform(REGION_COORDS[region]["lon_min"], REGION_COORDS[region]["lon_max"]), 5)
                location_writer.writerow([patient_id, lat, lon])

    print(f"✅ {count} unique patient records generated for {region} → {patient_file}")
    print(f"📍 Organ donor locations saved → {location_file}")


# ----------------------------
# STEP 3: Run the pipeline
# ----------------------------
if __name__ == "__main__":
    doctors = generate_doctors(NUM_DOCTORS)
    save_doctors_csv(doctors)

    for region in REGIONS:
        generate_patients(region, doctors, PATIENTS_PER_REGION)

    print("🎯 All regional doctor, patient, and organ donor location files (West & Central) generated successfully.")
