from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Plant, PlantFile
from app.schemas import FileCreate, FileTypeEnum, FileStatusEnum


# ========= FILE =========
def create_file(db: Session, data: FileCreate):
    db_file = PlantFile(**data.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def get_file(db: Session, file_id: int):
    return db.query(PlantFile).filter(PlantFile.id == file_id).first()


def get_files(
    db: Session, plant_id: Optional[str] = None, file_type: Optional[str] = None
):
    query = db.query(PlantFile)
    if plant_id:
        query = query.filter(PlantFile.plant_id == plant_id)
    if file_type:
        query = query.filter(PlantFile.file_type == file_type)
    return query.all()


def delete_file(db: Session, file_id: int):
    file = get_file(db, file_id)
    if file:
        db.delete(file)
        db.commit()
    return file


def get_plant_files(
    db: Session,
    plant_code: str,
    file_type: FileTypeEnum,
    date: Optional[date] = None,
    breeder_id: Optional[int] = None,
):
    query = (
        db.query(PlantFile)
        .join(Plant)
        .filter(Plant.plant_code == plant_code, PlantFile.file_type == file_type)
    )
    if breeder_id:
        query = query.filter(Plant.breeder_id == breeder_id)
    if date:
        query = query.filter(PlantFile.date == date)
    return query.all()


def create_plant_file(
    db: Session,
    plant_id: str,
    date: date,
    file_path: str,
    file_type: str,
    status: str = FileStatusEnum.PENDING,
    breeder_id: Optional[int] = None,
):
    # Check if plant exists and belongs to breeder
    if breeder_id:
        plant = (
            db.query(Plant)
            .filter(Plant.id == plant_id, Plant.breeder_id == breeder_id)
            .first()
        )
        if not plant:
            raise ValueError("Plant not found or does not belong to breeder")
    # Plant exists for that breeder_id (or admin case)
    file_obj = PlantFile(
        plant_id=plant_id,
        date=date,
        file_path=file_path,
        file_type=file_type,
        status=status,
    )
    db.add(file_obj)
    db.commit()
    db.refresh(file_obj)
    return file_obj


def update_file_status(
    db: Session, file_id: int, new_status: FileStatusEnum
) -> PlantFile:
    file_record = db.query(PlantFile).filter(PlantFile.id == file_id).first()
    if not file_record:
        return None
    file_record.status = new_status
    db.commit()
    db.refresh(file_record)
    return file_record
