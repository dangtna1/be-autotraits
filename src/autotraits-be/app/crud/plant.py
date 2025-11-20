from typing import Optional
from fastapi import HTTPException

from sqlalchemy.orm import Session
from app.db.models import Plant
from app.schemas import PlantCreate, PlantUpdate


# ========= PLANT =========
def create_plant(db: Session, plant: PlantCreate, breeder_id: int):
    # Check if plant_code already exists for that breeder
    existing = db.query(Plant).filter(Plant.plant_code == plant.plant_code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Plant with plant_code {plant.plant_code} already exists",
        )
    db_plant = Plant(**plant.dict(), breeder_id=breeder_id)
    db.add(db_plant)
    db.commit()
    db.refresh(db_plant)
    return db_plant


def get_plant(db: Session, plant_id: str, breeder_id: Optional[int] = None):
    query = db.query(Plant).filter(Plant.id == plant_id)
    if breeder_id:
        query = query.filter(Plant.breeder_id == breeder_id)
    return query.first()


# def get_plant_by_code(db: Session, plant_code: str, breeder_id: int):
#     query = db.query(Plant).filter(Plant.plant_code == plant_code and Plant.breeder_id == breeder_id)
#     return query.first()


def get_all_plants(
    db: Session, breeder_id: Optional[int] = None, offset: int = 0, limit: int = 10
):
    query = db.query(Plant)
    if breeder_id:
        query = query.filter(Plant.breeder_id == breeder_id)

    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return total, items


# delete plant by plant_code (should implement delete by plant_id later?)
# def delete_plant_by_code(db: Session, plant_code: str, breeder_id: int):
#     plant = get_plant_by_code(db, plant_code, breeder_id)
#     if not plant:
#         raise HTTPException(status_code=404, detail="Plant not found")

#     db.delete(plant)
#     db.commit()
#     return plant


# update plant by plant_id
def update_plant(db: Session, plant_id: int, plant: PlantUpdate, breeder_id: int):
    db_plant = get_plant(db, plant_id, breeder_id)
    if not db_plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    update_data = plant.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_plant, k, v)
    db.commit()
    db.refresh(db_plant)
    return db_plant


# delete plant by plant_id
def delete_plant(db: Session, plant_id: int, breeder_id: int):
    plant = get_plant(db, plant_id, breeder_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    db.delete(plant)
    db.commit()
    return plant
