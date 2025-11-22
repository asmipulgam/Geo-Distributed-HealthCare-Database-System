from faker import Faker
import csv
import random
import usgeocoder
from uszipcode import SearchEngine
from pathlib import Path

search = SearchEngine()  # faster

fake = Faker('en_US')

# ----------------------------
# CONFIGURATION
# ----------------------------
NUM_DOCTORS = 10000
PATIENTS_PER_REGION = 90000
# Regions to generate
REGIONS = ["us-west", "us-central"]#, "us-east"]

# State -> region mapping (as provided)
STATE_TO_REGION = {
  "AL": "us-east",
  "AK": "us-west",
  "AZ": "us-west",
  "AR": "us-central",
  "CA": "us-west",
  "CO": "us-west",
  "CT": "us-east",
  "DE": "us-east",
  "FL": "us-east",
  "GA": "us-east",
  "HI": "us-west",
  "ID": "us-west",
  "IL": "us-central",
  "IN": "us-central",
  "IA": "us-central",
  "KS": "us-central",
  "KY": "us-central",
  "LA": "us-central",
  "ME": "us-east",
  "MD": "us-east",
  "MA": "us-east",
  "MI": "us-central",
  "MN": "us-central",
  "MS": "us-central",
  "MO": "us-central",
  "MT": "us-west",
  "NE": "us-central",
  "NV": "us-west",
  "NH": "us-east",
  "NJ": "us-east",
  "NM": "us-west",
  "NY": "us-east",
  "NC": "us-east",
  "ND": "us-central",
  "OH": "us-central",
  "OK": "us-central",
  "OR": "us-west",
  "PA": "us-east",
  "RI": "us-east",
  "SC": "us-east",
  "SD": "us-central",
  "TN": "us-central",
  "TX": "us-central",
  "UT": "us-west",
  "VT": "us-east",
  "VA": "us-east",
  "WA": "us-west",
  "WV": "us-east",
  "WI": "us-central",
  "WY": "us-west"
}

# Invert mapping: region -> list of states
REGION_TO_STATES = {}
for st, rg in STATE_TO_REGION.items():
    REGION_TO_STATES.setdefault(rg, []).append(st)

# Define rough coordinate ranges per region (approximate USA ranges)
REGION_COORDS = {
    "us-west": {
        "lat_min": 32.0, "lat_max": 49.0,   # California to Washington
        "lon_min": -124.5, "lon_max": -112.0
    },
    "us-central": {
        "lat_min": 29.0, "lat_max": 49.0,   # Texas to Minnesota
        "lon_min": -105.0, "lon_max": -90.0
    },
    "us-east": {
        "lat_min": 25.0, "lat_max": 45.0,   # Florida up to New England
        "lon_min": -90.0, "lon_max": -70.0
    }
}

# Cache of state -> list of real ZIP codes (populated on demand)
ZIP_CACHE = {}

def get_zip_for_state(state_abbr):
    """Return a real ZIP code for the given state abbreviation using uszipcode.
    Caches the per-state list for speed. Falls back to Faker if lookup fails.
    """
    state_abbr = (state_abbr or '').upper()
    if not state_abbr:
        return fake.zipcode()
    if state_abbr in ZIP_CACHE:
        zs = ZIP_CACHE[state_abbr]
        return random.choice(zs) if zs else fake.zipcode_in_state(state_abbr)

    zips = []
    try:
        # try to fetch many zipcodes for the state; returns list of SimpleZipcode objects
        results = search.by_state(state_abbr, returns=5000)
        for z in results:
            code = getattr(z, 'zipcode', None) or getattr(z, 'zip', None)
            if code:
                zips.append(code)
    except Exception:
        # uszipcode API may differ; attempt a smaller fetch or fallback
        try:
            results = search.by_state(state_abbr)
            for z in results:
                code = getattr(z, 'zipcode', None) or getattr(z, 'zip', None)
                if code:
                    zips.append(code)
        except Exception:
            zips = []

    # filter and dedupe
    zips = list({s for s in zips if isinstance(s, str) and s.strip()})
    ZIP_CACHE[state_abbr] = zips
    if zips:
        return random.choice(zips)
    # final fallback: use faker
    try:
        return fake.zipcode_in_state(state_abbr)
    except Exception:
        return fake.zipcode()

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
        region = random.choice(REGIONS)
        doctors.append({
            "Doctor_ID": doctor_id,
            "Doctor_Name": fake.name(),
            "Hospital": fake.company(),
            "Region": region
        })
    return doctors


def save_doctors_csv(doctors):
    data_dir = Path(__file__).resolve().parent.parent / 'central_backend' / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "Doctors.csv"
    with out_path.open("w", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Doctor_ID", "Doctor_Name", "Hospital", "Region"])
        for d in doctors:
            writer.writerow([d["Doctor_ID"], d["Doctor_Name"], d["Hospital"], d["Region"]])
    print(f"{len(doctors)} doctor records written → {out_path}")


# ----------------------------
# STEP 2: Generate Patient Tables + Locations
# ----------------------------
def generate_patients(region, doctors, count):
    data_dir = Path(__file__).resolve().parent.parent / 'central_backend' / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    patient_file = data_dir / f"Patients_{region.upper()}.csv"

    with patient_file.open("w", newline="", encoding="utf-8") as pf:
        
        patient_writer = csv.writer(pf)

        # Headers (Phone removed) — use boolean is_organ_donor column
        patient_writer.writerow([
            "Patient_ID", "Patient_Name", "Doctor_ID", "Doctor_Name",
            "Age", "Gender", "Phone","Email", "Address", "State",
            "Region", "Appointment_Date", "Diagnosis", "Date_of_Birth", "is_organ_donor",
            "lat","lon"
        ])
        

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
            # boolean flag for organ donor
            is_organ_donor = random.choice([True, False])
            # choose a state belonging to this region
            state_choice = random.choice(REGION_TO_STATES.get(region, ["UNKNOWN"]))

            # Build address components with a ZIP tied to the chosen state when possible
            street = fake.street_address()
            city = fake.city()
            zipcode = get_zip_for_state(state_choice)

            address = f"{street}, {city}, {state_choice} {zipcode}"

            # Prefer uszipcode lookup by ZIP for coordinates (fast, offline)
            lat = None
            lon = None
            try:
                z = search.by_zipcode(zipcode)
                if z and getattr(z, 'lat', None) is not None and getattr(z, 'lng', None) is not None:
                    lat = round(z.lat, 5)
                    lon = round(z.lng, 5)
            except Exception:
                lat = None
                lon = None

            # Fallback: sample lat/lon within region bounds if uszipcode lookup failed
            if lat is None or lon is None:
                lat = round(random.uniform(REGION_COORDS[region]["lat_min"], REGION_COORDS[region]["lat_max"]), 5)
                lon = round(random.uniform(REGION_COORDS[region]["lon_min"], REGION_COORDS[region]["lon_max"]), 5)
            # Write patient record
            patient_writer.writerow([
                patient_id,
                fake.name(),
                doctor["Doctor_ID"],
                doctor["Doctor_Name"],
                age,
                gender,
                fake.phone_number(),
                fake.email(),
                address,
                state_choice,
                region,
                fake.date_between(start_date='-2y', end_date='today'),
                random.choice([
                    "Diabetes", "Hypertension", "Flu", "Asthma", "Back Pain",
                    "Covid-19", "Allergy", "Migraine", "Anxiety", "Arthritis"
                ]),
                dob,
                is_organ_donor,
                lat,
                lon
            ])

    print(f" {count} unique patient records generated for {region} → {patient_file}")


# ----------------------------
# STEP 3: Run the pipeline
# ----------------------------
if __name__ == "__main__":
    doctors = generate_doctors(NUM_DOCTORS)
    save_doctors_csv(doctors)

    for region in REGIONS:
        generate_patients(region, doctors, PATIENTS_PER_REGION)

    print(" All regional doctor and patient records generated successfully.")