import csv
import io
import pandas as pd
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import app.crud as crud
from app.db.models import Role, User
from app.dependencies import get_db, get_current_user
from app.schemas import (
    PaginatedResponse,
    MeasurementCreate,
    MeasurementInDB,
    MeasurementUpdate,
)

router = APIRouter()


# ========== MEASUREMENTS ==========
@router.post("/measurements", response_model=MeasurementInDB)
def create_measurement_route(
    measurement: MeasurementCreate,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    if not measurement.plant_id:
        raise HTTPException(status_code=400, detail="plant_id is required")

    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id is required")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot create measurement for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    return crud.create_measurement(db, measurement, breeder_id=final_breeder_id)


@router.get("/measurements", response_model=PaginatedResponse[MeasurementInDB])
def list_measurements_route(
    plant_code: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    variety: Optional[str] = None,
    field: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        total, items = crud.get_measurements(
            db, plant_code, start_date, end_date, offset=offset, limit=limit
        )
    else:
        total, items = crud.get_measurements(
            db,
            plant_code,
            start_date,
            end_date,
            variety,
            field,
            offset=offset,
            limit=limit,
            breeder_id=current_user.breeder_id,
        )
    return {"total": total, "offset": offset, "limit": limit, "items": items}


@router.get("/measurements/download-template")
def download_measurement_template():
    headers = [
        "plant_code",
        "date",
        "variety",
        "biomass",
        "canopy_density",
        "part_ripe",
        "unripe",
        "flower",
        "fruit_width",
        "fruit_height",
        "mass",
        "yield_per_plant",
        "cum_yield_per_plant",
        "class_1",
        "length_of_cropping",
        "field",
        "petiole_length",
        "petiole_strength",
        "petiole_radius",
        "truss_length",
        "truss_strength",
        "truss_radius",
        "growth_habit",
        "fruit_shape",
        "crop_composition",
        "plant_height",
        "exg",
    ]

    # Example sample row
    sample_row = [
        "AA11",  # plant_code
        "20250506",  # date (YYYY-MM-DD)
        "Falco",  # variety
        None,  # biomass
        None,  # canopy_density
        0,  # part_ripe
        6,  # unripe
        4,  # flower
        "[]",  # fruit_width as list string
        "[]",  # fruit_height as list string
        "[]",  # mass as list string
        0,  # yield_per_plant
        None,  # cum_yield_per_plant
        None, # class_1
        None,  # length_of_cropping
        "A",  # field
        None,  # petiole_length
        None,  # petiole_strength
        None,  # petiole_radius
        None,  # truss_length
        None,  # truss_strength
        None,  # truss_radius
        None, # growth_habit
        None, # fruit_shape
        0,  # crop_composition
        27.09,  # plant_height
        39.499,  # exg
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerow(sample_row)  # add sample row
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=measurement_template.csv"
        },
    )


@router.post("/measurements/import")
def import_measurements(
    file: UploadFile = File(...),
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Breeder validation
    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id is required")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot import for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    try:
        df = pd.read_csv(file.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")

    result = crud.bulk_import_measurements(db, df, final_breeder_id)
    return result


@router.get("/measurements/{measurement_id}", response_model=MeasurementInDB)
def get_measurement_route(
    measurement_id: int,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id is required")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot access measurement for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    measurement = crud.get_measurement(db, measurement_id, final_breeder_id)

    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return measurement


@router.put("/measurements/{measurement_id}", response_model=MeasurementInDB)
def update_measurement_route(
    measurement_id: int,
    measurement: MeasurementUpdate,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id is required")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot update measurement for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    return crud.update_measurement(
        db, measurement_id, measurement, breeder_id=final_breeder_id
    )


@router.delete("/measurements/{measurement_id}", response_model=MeasurementInDB)
def delete_measurement_route(
    measurement_id: int,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id is required")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot delete measurement for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    measurement = crud.delete_measurement(
        db, measurement_id, breeder_id=final_breeder_id
    )
    return measurement


# ====== AGGREGATED SUMMARY ======
@router.get("/summary")
def get_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns aggregated dashboard data for the current user's breeder_id:
    - total plants
    - unique varieties
    - number of samples per variety
    - last measured date
    Supports optional start_date and end_date filters.
    """
    return crud.get_summary(db, current_user.breeder_id, start_date, end_date)


@router.get("/plant/{plant_code}/unique-measurement-dates", response_model=List[date])
def get_unique_dates(
    plant_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        dates = crud.get_unique_measurement_dates(db, plant_code)
    else:
        dates = crud.get_unique_measurement_dates(
            db, plant_code, breeder_id=current_user.breeder_id
        )
    return dates
