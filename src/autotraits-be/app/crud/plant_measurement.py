import json
import math
from typing import Optional
from fastapi import HTTPException
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import app.crud as crud

from app.db.models import Plant, PlantFruit, PlantMeasurement

from app.schemas import PlantCreate, FruitCreate, MeasurementCreate, MeasurementUpdate


# ========= MEASUREMENT =========
def validate_measurement(measurement_dict: dict, fruits_data: list):
    # Non-negative integers
    for field in [
        "part_ripe",
        "unripe",
        "flower",
        "biomass",
        "canopy_density",
        "yield_per_plant",
        "cum_yield_per_plant",
        "class_1",
        "length_of_cropping",
        "petiole_length",
        "petiole_strength",
        "petiole_radius",
        "truss_length",
        "truss_strength",
        "truss_radius",
        "crop_composition",
        "plant_height",
        "exg",
    ]:
        if field in measurement_dict and measurement_dict[field] is not None:
            if measurement_dict[field] < 0:
                raise HTTPException(
                    status_code=400, detail=f"{field} must be non-negative"
                )

    # Fruits
    for i, fruit in enumerate(fruits_data):
        for attr in ["width", "height", "mass"]:
            val = getattr(fruit, attr)
            if val is not None and val < 0:
                raise HTTPException(
                    status_code=400, detail=f"Fruit {i} {attr} must be non-negative"
                )


def create_measurement(db: Session, data: MeasurementCreate, breeder_id: int):
    # 1. Ensure plant exists
    plant = (
        db.query(Plant)
        .filter(Plant.id == data.plant_id, Plant.breeder_id == breeder_id)
        .first()
    )
    if not plant:
        raise HTTPException(
            status_code=404, detail="Plant not found or does not belong to breeder"
        )

    # 2. Check uniqueness constraint (plant_id, date)
    existing = (
        db.query(PlantMeasurement)
        .filter(
            PlantMeasurement.plant_id == plant.id,
            PlantMeasurement.date == data.date,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Measurement for plant {data.plant_id} on date {data.date} already exists",
        )

    # 3. Prepare measurement data (exclude fruits)
    measurement_data = data.dict(exclude={"fruits"})

    # Validate before inserting
    validate_measurement(measurement_data, data.fruits)

    # Set ripe to match number of fruits
    measurement_data["ripe"] = len(data.fruits)

    db_measurement = PlantMeasurement(**measurement_data)
    db.add(db_measurement)
    db.flush()  # ensures db_measurement.id is available

    # 4. Add fruits (if any)
    for fruit in data.fruits:
        db.add(PlantFruit(**fruit.dict(), measurement_id=db_measurement.id))

    db.commit()
    db.refresh(db_measurement)
    return db_measurement


def update_measurement(
    db: Session, measurement_id: int, data: MeasurementUpdate, breeder_id: int
):
    # 1. Find measurement
    measurement = (
        db.query(PlantMeasurement)
        .join(Plant)
        .filter(
            PlantMeasurement.id == measurement_id,
            Plant.breeder_id == breeder_id,
        )
        .first()
    )
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    # 2. If date changed, enforce uniqueness (plant_id, date)
    if data.date is not None and data.date != measurement.date:
        existing = (
            db.query(PlantMeasurement)
            .filter(
                PlantMeasurement.plant_id == measurement.plant_id,
                PlantMeasurement.date == data.date,
                PlantMeasurement.id != measurement.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Measurement for plant {measurement.plant_id} on date {data.date} already exists",
            )

    # 3. Update scalar fields (exclude fruits + ripe)
    update_data = data.dict(exclude_unset=True, exclude={"fruits", "ripe"})
    for k, v in update_data.items():
        setattr(measurement, k, v)

    # Validate before updating
    fruits_data = (
        data.fruits
        if data.fruits is not None
        else [
            FruitCreate(width=f.width, height=f.height, mass=f.mass)
            for f in measurement.fruits
        ]
    )
    validate_measurement({**measurement.__dict__, **update_data}, fruits_data)

    # 4. Replace fruits if provided
    if data.fruits is not None:
        # delete all old fruits at once
        db.query(PlantFruit).filter_by(measurement_id=measurement.id).delete(
            synchronize_session=False
        )

        # add new fruits
        for fruit in data.fruits:
            db.add(PlantFruit(**fruit.dict(), measurement_id=measurement.id))

        # update ripe count
        measurement.ripe = len(data.fruits)

    db.commit()
    db.refresh(measurement)
    return measurement


def upsert_measurement(db: Session, data: MeasurementCreate, breeder_id: int):
    plant = (
        db.query(Plant)
        .filter(Plant.id == data.plant_id, Plant.breeder_id == breeder_id)
        .first()
    )
    if not plant:
        raise HTTPException(
            status_code=404, detail="Plant not found or does not belong to breeder"
        )

    db_measurement = (
        db.query(PlantMeasurement)
        .filter(
            PlantMeasurement.plant_id == data.plant_id,
            PlantMeasurement.date == data.date,
        )
        .first()
    )

    measurement_data = data.dict(exclude={"fruits"})
    measurement_data["ripe"] = len(data.fruits)

    # Validate before insert/update
    validate_measurement(measurement_data, data.fruits)

    if db_measurement:
        # Update
        for k, v in measurement_data.items():
            setattr(db_measurement, k, v)
        db.query(PlantFruit).filter(
            PlantFruit.measurement_id == db_measurement.id
        ).delete()
        for fruit in data.fruits:
            db.add(PlantFruit(**fruit.dict(), measurement_id=db_measurement.id))
    else:
        # Insert
        db_measurement = PlantMeasurement(**measurement_data)
        db.add(db_measurement)
        db.flush()
        for fruit in data.fruits:
            db.add(PlantFruit(**fruit.dict(), measurement_id=db_measurement.id))

    db.commit()
    db.refresh(db_measurement)
    return db_measurement


def bulk_import_measurements(db: Session, df, breeder_id: int):
    """
    df: pandas DataFrame from CSV
    breeder_id: breeder to assign measurements to
    Returns: dict with inserted, updated, errors
    """
    inserted, updated, errors = 0, 0, []

    for idx, row in df.iterrows():
        try:
            measurement_dict = row.to_dict()

            # === Sanitize numeric fields ===
            for key, value in measurement_dict.items():
                if isinstance(value, float) and (
                    math.isnan(value) or math.isinf(value)
                ):
                    measurement_dict[key] = None

            # === Process fruit arrays ===
            fruit_widths = json.loads(measurement_dict.get("fruit_width", "[]"))
            fruit_heights = json.loads(measurement_dict.get("fruit_height", "[]"))
            fruit_masses = json.loads(measurement_dict.get("mass", "[]"))

            if not (len(fruit_widths) == len(fruit_heights) == len(fruit_masses)):
                raise ValueError(
                    f"fruit_width, fruit_height, and mass must have the same length at row {idx}"
                )

            # Sanitize fruit numeric values
            def sanitize_float_list(lst):
                return [float(x) if x not in (None, "", "NaN") else None for x in lst]

            fruits_data = [
                FruitCreate(width=w, height=h, mass=m)
                for w, h, m in zip(
                    sanitize_float_list(fruit_widths),
                    sanitize_float_list(fruit_heights),
                    sanitize_float_list(fruit_masses),
                )
            ]

            # Remove fruit columns from measurement dict
            for col in ["fruit_width", "fruit_height", "mass"]:
                measurement_dict.pop(col, None)

            # === Map plant_code to plant_id ===
            plant_code = measurement_dict.pop("plant_code")
            plant = (
                db.query(Plant)
                .filter(Plant.plant_code == plant_code, Plant.breeder_id == breeder_id)
                .first()
            )
            if not plant:
                plant = crud.create_plant(
                    db, PlantCreate(plant_code=plant_code), breeder_id=breeder_id
                )

            measurement_dict["plant_id"] = plant.id

            # === Convert date strings to datetime.date ===
            date_str = measurement_dict.get("date")
            if date_str:
                try:
                    date_str = str(date_str)
                    if len(date_str) == 8 and date_str.isdigit():  # YYYYMMDD
                        measurement_dict["date"] = datetime.strptime(
                            date_str, "%Y%m%d"
                        ).date()
                    else:
                        try:
                            measurement_dict["date"] = datetime.strptime(
                                date_str, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            measurement_dict["date"] = datetime.strptime(
                                date_str, "%d/%m/%Y"
                            ).date()
                except ValueError:
                    raise ValueError(f"Invalid date format at row {idx}: {date_str}")

            # === Create Pydantic model ===
            measurement = MeasurementCreate(**measurement_dict, fruits=fruits_data)

            # Validate (your custom function)
            validate_measurement(measurement_dict, fruits_data)

            # === Upsert measurement ===
            existing = (
                db.query(PlantMeasurement)
                .filter(
                    PlantMeasurement.plant_id == measurement.plant_id,
                    PlantMeasurement.date == measurement.date,
                )
                .first()
            )

            upsert_measurement(db, measurement, breeder_id=breeder_id)

            if existing:
                updated += 1
            else:
                inserted += 1

        except Exception as e:
            errors.append({"row": idx, "error": str(e)})

    return {"inserted": inserted, "updated": updated, "errors": errors}


def get_measurement(db: Session, measurement_id: int, breeder_id: int):
    query = (
        db.query(PlantMeasurement)
        .join(Plant)
        .options(
            joinedload(PlantMeasurement.fruits), joinedload(PlantMeasurement.plant)
        )
        .filter(PlantMeasurement.id == measurement_id, Plant.breeder_id == breeder_id)
    )

    return query.first()


def get_measurements(
    db: Session,
    plant_code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    variety: Optional[str] = None,
    field: Optional[str] = None,
    offset: int = 0,
    limit: int = 10,
    breeder_id: Optional[int] = None,
):
    # Base query with join
    query = db.query(
        PlantMeasurement,
        func.sum(PlantMeasurement.ripe)
        .over(partition_by=PlantMeasurement.plant_id, order_by=PlantMeasurement.date)
        .label("cumulative_ripe"),
    ).outerjoin(Plant)

    # Filters
    if breeder_id:
        query = query.filter(Plant.breeder_id == breeder_id)
    if plant_code:
        query = query.filter(Plant.plant_code == plant_code)
    if start_date:
        query = query.filter(PlantMeasurement.date >= start_date)
    if end_date:
        query = query.filter(PlantMeasurement.date <= end_date)
    if variety:
        query = query.filter(PlantMeasurement.variety == variety)
    if field:
        query = query.filter(PlantMeasurement.field == field)

    # Count total (need to count from subquery or base model)
    total = query.count()

    # Pagination + loading relationships
    items = (
        query.options(
            joinedload(PlantMeasurement.plant),
            joinedload(PlantMeasurement.fruits),
        )
        .order_by(PlantMeasurement.date)
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Convert to list of dicts with cumulative value added
    results = []
    for measurement, cumulative_ripe in items:
        m_dict = measurement.__dict__.copy()
        m_dict["cumulative_ripe"] = cumulative_ripe
        results.append(m_dict)

    return total, results


def delete_measurement(db: Session, measurement_id: int, breeder_id: int):
    measurement = get_measurement(db, measurement_id, breeder_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")

    db.delete(measurement)
    db.commit()
    return measurement


def get_summary(
    db: Session,
    breeder_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    # Get plant IDs for this breeder
    plant_ids = db.query(Plant.id).filter(Plant.breeder_id == breeder_id).subquery()

    # Base measurement query
    query = db.query(PlantMeasurement).filter(PlantMeasurement.plant_id.in_(plant_ids))
    if start_date:
        query = query.filter(PlantMeasurement.date >= start_date)
    if end_date:
        query = query.filter(PlantMeasurement.date <= end_date)

    # ---- Total plants ----
    total_plants = (
        db.query(func.count(Plant.id)).filter(Plant.breeder_id == breeder_id).scalar()
    )

    # ---- Unique varieties ----
    unique_varieties = (
        db.query(PlantMeasurement.variety)
        .filter(PlantMeasurement.plant_id.in_(plant_ids))
        .filter(PlantMeasurement.variety.isnot(None))
        .distinct()
        .all()
    )
    unique_varieties = [v[0] for v in unique_varieties]

    # ---- Unique fields ----
    unique_fields = (
        db.query(PlantMeasurement.field)
        .filter(PlantMeasurement.plant_id.in_(plant_ids))
        .filter(PlantMeasurement.field.isnot(None))
        .distinct()
        .all()
    )
    unique_fields = [f[0] for f in unique_fields]

    # ---- Samples per variety ----
    samples_per_variety = dict(
        db.query(PlantMeasurement.variety, func.count(PlantMeasurement.id))
        .filter(PlantMeasurement.plant_id.in_(plant_ids))
        .group_by(PlantMeasurement.variety)
        .all()
    )

    # ---- Last measured date ----
    last_measured_date = query.with_entities(func.max(PlantMeasurement.date)).scalar()

    return {
        "total_plants": total_plants,
        "unique_varieties": list(unique_varieties),
        "unique_fields": list(unique_fields),
        "samples_per_variety": dict(samples_per_variety),
        "last_measured_date": (
            last_measured_date.isoformat() if last_measured_date else None
        ),
    }


def get_unique_measurement_dates(
    db: Session, plant_code: str, breeder_id: Optional[int] = None
):
    query = (
        db.query(PlantMeasurement.date)
        .join(Plant)
        .filter(Plant.plant_code == plant_code)
    )
    if breeder_id:
        query = query.filter(Plant.breeder_id == breeder_id)
    dates = query.distinct().order_by(PlantMeasurement.date).all()
    return [d[0] for d in dates]  # Unpack tuples
