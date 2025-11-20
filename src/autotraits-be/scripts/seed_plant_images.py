from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from tqdm import tqdm

from app.db.models import PlantFile, Plant
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


def seed_plant_images(filepath: str, breeder_id: int = DEFAULT_BREEDER_ID):
    df = pd.read_csv(filepath, delimiter=",")

    # Rename columns to match DB model
    df.rename(
        columns={
            "ID": "plant_code",
            "Date": "date",
            "FilePath": "file_path",
            "FileType": "file_type",
        },
        inplace=True,
    )

    df["date"] = df["date"].apply(lambda x: parse_date(x) if pd.notnull(x) else None)
    df = df.where(pd.notnull(df), None)

    session = SessionLocal()
    try:
        # Ensure plants exist first
        plant_codes = df["plant_code"].unique().tolist()
        ensure_plants_exist(session, plant_codes)

        # Build mapping plant_code -> plant.id
        plant_map = {
            p.plant_code: p.id
            for p in session.query(Plant).filter(
                Plant.plant_code.in_(plant_codes), Plant.breeder_id == breeder_id
            )
        }

        skip_count = 0
        for _, row in tqdm(df.iterrows(), total=len(df)):
            row_dict = row.to_dict()
            plant_id = plant_map[row_dict["plant_code"]]

            existing = (
                session.query(PlantFile)
                .filter_by(
                    plant_id=plant_id,
                    date=row_dict["date"],
                    file_path=row_dict["file_path"],
                    file_type=row_dict["file_type"],
                )
                .first()
            )

            if existing:
                skip_count += 1
                print(
                    f"Skipping existing record for plant {row_dict['plant_code']} on {row['date']}"
                )
                continue

            row_dict["plant_id"] = plant_id
            row_dict.pop("plant_code")
            entry = PlantFile(**row_dict)
            session.add(entry)

        session.commit()
        print(f"Imported {len(df) - skip_count} file path records from {filepath}")
    except Exception as e:
        session.rollback()
        print(f"Error importing file paths: {e}")
    finally:
        session.close()


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python seed_plant_images.py <csv_path>")
        sys.exit(1)

    seed_plant_images(sys.argv[1])


if __name__ == "__main__":
    main()
