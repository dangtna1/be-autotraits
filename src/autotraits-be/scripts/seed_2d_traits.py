import ast
import math
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.db.models import Plant, PlantMeasurement, PlantFruit
from app.db.session import SessionLocal
from tqdm import tqdm

DEFAULT_BREEDER_ID = 1  # adjust if needed


def clean_nan_dict(d):
    return {
        k: None if (isinstance(v, float) and math.isnan(v)) else v for k, v in d.items()
    }


def parse_date(d):
    return datetime.strptime(str(d), "%Y%m%d").date()


def parse_list_field(val):
    """
    Convert string like "[59.0, 40.0]" into Python list.
    Empty list "[]" stays as [].
    NaN/None stays as [].
    """
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return []
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return parsed
            return []
        except Exception:
            return []
    if isinstance(val, list):
        return val
    return []


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


def seed_2d_traits(csv_path: str, breeder_id: int = DEFAULT_BREEDER_ID):
    df = pd.read_csv(csv_path)

    # Rename columns to match DB model
    df.rename(
        columns={
            "ID": "plant_code",
            "Date": "date",
            "Variety": "variety",
            "Ripe": "ripe",
            "Part-ripe": "part_ripe",
            "Unripe": "unripe",
            "Flower": "flower",
            "Fruit-width": "fruit_width",
            "Fruit-height": "fruit_height",
            "Mass": "mass",
            "Yield/plant": "yield_per_plant",
            "Crop-composition": "crop_composition",
            "Plant-height": "plant_height",
            "ExG": "exg",
        },
        inplace=True,
    )

    df["date"] = df["date"].apply(parse_date)
    df = df.where(pd.notnull(df), None)

    session: Session = SessionLocal()
    try:
        # Ensure plants exist
        plant_codes = df["plant_code"].unique().tolist()
        ensure_plants_exist(session, plant_codes, breeder_id)

        # Build mapping plant_code -> plant.id
        plant_map = {
            p.plant_code: p.id
            for p in session.query(Plant).filter(
                Plant.plant_code.in_(plant_codes), Plant.breeder_id == breeder_id
            )
        }

        # Insert or update measurements + fruits
        for _, row in tqdm(df.iterrows(), total=len(df)):
            row_dict = clean_nan_dict(row.to_dict())
            plant_id = plant_map[row_dict["plant_code"]]

            fruit_widths = parse_list_field(row_dict.pop("fruit_width"))
            fruit_heights = parse_list_field(row_dict.pop("fruit_height"))
            fruit_masses = parse_list_field(row_dict.pop("mass"))

            existing = (
                session.query(PlantMeasurement)
                .filter_by(plant_id=plant_id, date=row_dict["date"])
                .first()
            )

            if existing:
                # update scalar fields
                for key, value in row_dict.items():
                    if key != "plant_code":
                        setattr(existing, key, value)

                # Delete old fruits from DB
                session.query(PlantFruit).filter_by(measurement_id=existing.id).delete()
                session.flush()  # make sure deletion is applied immediately

                # Add new fruits
                for w, h, m in zip(fruit_widths, fruit_heights, fruit_masses):
                    existing.fruits.append(PlantFruit(width=w, height=h, mass=m))

            else:
                row_dict["plant_id"] = plant_id
                row_dict.pop("plant_code")

                measurement = PlantMeasurement(**row_dict)
                for w, h, m in zip(fruit_widths, fruit_heights, fruit_masses):
                    measurement.fruits.append(PlantFruit(width=w, height=h, mass=m))

                session.add(measurement)

        session.commit()
        print(f"Seeded {len(df)} 2D trait records (with fruits) from {csv_path}")

    except Exception as e:
        session.rollback()
        print(f"Error seeding measurements: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python seed_2d_traits.py <csv_path>")
        sys.exit(1)

    seed_2d_traits(sys.argv[1])
