import pandas as pd
from datetime import datetime
import requests
import concurrent.futures
from sqlalchemy.orm import Session
from app.db.models import Plant
from app.db.session import SessionLocal

DEFAULT_BREEDER_ID = 1  # adjust if needed


def parse_date(d):
    return datetime.strptime(str(d), "%Y%m%d").date()


def ensure_plants_exist(
    session: Session, plant_codes: list[str], breeder_id: int = DEFAULT_BREEDER_ID
):
    existing = (
        session.query(Plant.plant_code)
        .filter(Plant.plant_code.in_(plant_codes), Plant.breeder_id == breeder_id)
        .all()
    )
    existing_codes = {p[0] for p in existing}
    missing_codes = set(plant_codes) - existing_codes

    if missing_codes:
        session.bulk_save_objects(
            [Plant(plant_code=code, breeder_id=breeder_id) for code in missing_codes]
        )
        session.commit()
        print(
            f"Inserted {len(missing_codes)} new plants for breeder {breeder_id}: {missing_codes}"
        )


# Configuration - change as needed
plant_code = "AB34"  # change to your plant_code
filepath = r"D:\autotraits\autotraits\npec_data_processing\AB34_paths.csv"  # CSV file with: date,plant_code,file_type,extension,file_path - get from file "query_saved_data.py"
API_URL = (
    "http://localhost:8000/api/plant/{plant_id}/bulk-upload"  # change host if needed
)


# Step 0: Map plant_code to plant_id and ensure plant exists
with SessionLocal() as session:
    plant = (
        session.query(Plant)
        .filter(Plant.plant_code == plant_code, Plant.breeder_id == DEFAULT_BREEDER_ID)
        .first()
    )
    if not plant:
        ensure_plants_exist(session, [plant_code])
        plant = (
            session.query(Plant)
            .filter(
                Plant.plant_code == plant_code, Plant.breeder_id == DEFAULT_BREEDER_ID
            )
            .first()
        )
    plant_id = plant.id

# update API_URL with actual plant_id
API_URL = API_URL.format(plant_id=plant_id)

# Step 1: Read CSV into list of dicts
df = pd.read_csv(filepath, delimiter=",")
df = df.where(pd.notnull(df), None)

# keep local file paths separately
local_paths = df["file_path"].tolist()

# only send date, file_type, extension to API
files = df[["date", "file_type", "extension"]].to_dict("records")

# ensure date is str
for f in files:
    if f["date"]:
        f["date"] = str(f["date"])

print(f"Prepared {len(files)} files from CSV")

# Step 2: Call FastAPI bulk-upload
response = requests.post(API_URL, json={"files": files})
if response.status_code != 200:
    print("Failed to register files:", response.text)
    exit()

records = response.json()
print(f"Received {len(records)} upload URLs from API")


# Step 3: Upload each file to Azure
def upload_file(record, local_path):
    upload_url = record["upload_url"]
    try:
        with open(local_path, "rb") as f:
            resp = requests.put(
                upload_url, data=f, headers={"x-ms-blob-type": "BlockBlob"}
            )
        return (local_path, resp.status_code)
    except Exception as e:
        return (local_path, f"Error: {e}")


# Pair records with their corresponding local paths from original files
tasks = [(rec, path) for rec, path in zip(records, local_paths)]

# Step 4: Parallel upload
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(lambda x: upload_file(*x), tasks))

# Step 5: Print results
for file_path, status in results:
    print(f"{file_path} -> {status}")
    if status in [200, 201]:
        # Update file record as COMPLETED
        pass

# FInally, mark files as COMPLETED in database
completed_ids = [
    rec["db_id"]
    for rec, (path, status) in zip(records, results)
    if status in (200, 201)
]

if completed_ids:
    resp = requests.post(
        "http://localhost:8000/api/files/update-status",
        json={"ids": completed_ids, "status": "COMPLETED"},
    )
    if resp.status_code == 200:
        print(f"Marked {len(completed_ids)} files as COMPLETED")
    else:
        print("Batch update failed:", resp.text)
