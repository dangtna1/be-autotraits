import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session

from app.core.adls import generate_sas_url, upload_to_blob
from app.dependencies import get_db, get_current_user
import app.crud as crud
from app.db.models import Role, User, PlantFile

from app.schemas import (
    FileTypeEnum,
    FileStatusEnum,
    BulkUploadRequest,
    StatusUpdateRequest,
)

router = APIRouter()


# ========== FILES ==========
# @router.post("/files/", response_model=FileInDB)
# def create_file_route(file: FileCreate, db: Session = Depends(get_db)):
#     return crud.create_file(db, file)


# @router.get("/files/", response_model=List[FileInDB])
# def list_files_route(
#     plant_id: Optional[str] = None,
#     file_type: Optional[str] = None,
#     db: Session = Depends(get_db),
# ):
#     return crud.get_files(db, plant_id, file_type)


# @router.get("/files/{file_id}", response_model=FileInDB)
# def get_file_route(file_id: int, db: Session = Depends(get_db)):
#     file = crud.get_file(db, file_id)
#     if not file:
#         raise HTTPException(status_code=404, detail="File not found")
#     return file


# @router.delete("/files/{file_id}", response_model=FileInDB)
# def delete_file_route(file_id: int, db: Session = Depends(get_db)):
#     return crud.delete_file(db, file_id)


@router.get("/plant/{plant_code}/images")
def get_plant_images(
    plant_code: str,
    file_type: FileTypeEnum,  # This expects 'TWO_D' or 'THREE_D'
    date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role == Role.ADMIN:
            files = crud.get_plant_files(db, plant_code, file_type, date)
        else:
            files = crud.get_plant_files(
                db, plant_code, file_type, date, current_user.breeder_id
            )

        result = []
        for f in files:
            sas_url = generate_sas_url(f.file_path)
            result.append(
                {
                    "id": f.id,
                    "plant_id": f.plant_id,
                    "url": sas_url,
                    "file_type": f.file_type,
                    "date": f.date,
                    "status": f.status,
                }
            )
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plant/{plant_id}/upload-file")
def create_upload_and_register(
    plant_id: str,
    date: date,
    file_type: FileTypeEnum,
    extension: str,  # let client specify, e.g. "jpg", "png", "ply"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an upload SAS URL and register the file in DB as 'pending'.
    """
    try:
        # Generate blob path
        blob_name = f"{uuid.uuid4()}.{extension}"
        # Generate upload SAS URL
        upload_url = generate_sas_url(blob_name, isUpload=True)
        # Register in DB
        file_record = crud.create_plant_file(
            db=db,
            plant_id=plant_id,
            date=date,
            file_path=blob_name,
            file_type=file_type,
            breeder_id=(
                current_user.breeder_id if current_user.role != Role.ADMIN else None
            ),
            status=FileStatusEnum.PENDING,
        )
        return {
            "upload_url": upload_url,
            "blob_path": blob_name,
            "db_id": file_record.id,
            "status": file_record.status,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAS generation failed: {str(e)}")


# user upload multi-part/form data
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/plant/{plant_id}/upload-file-v2")
async def upload_plant_file(
    plant_id: str,
    date: date = Form(...),
    file_type: FileTypeEnum = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file + metadata in one request (multipart/form-data).
    Uses two-step workflow: PENDING -> COMPLETED/FAILED to record every attempt.
    """
    # Validate extension
    extension = file.filename.split(".")[-1].lower()
    if extension not in ["png", "ply"]:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    # Check if extension matches file_type
    if (file_type == FileTypeEnum.TWO_D and extension != "png") or (
        file_type == FileTypeEnum.THREE_D and extension != "ply"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"File extension {extension} does not match file_type {file_type}",
        )

    # Check size
    file.file.seek(0, 2)  # move pointer to end
    size = file.file.tell()
    file.file.seek(0)  # reset pointer for upload
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Generate blob name
    blob_name = f"{uuid.uuid4()}.{extension}"

    # Step 1: Insert DB record as PENDING
    file_record = crud.create_plant_file(
        db=db,
        plant_id=plant_id,
        date=date,
        file_path=blob_name,
        file_type=file_type,
        breeder_id=(
            current_user.breeder_id if current_user.role != Role.ADMIN else None
        ),
        status=FileStatusEnum.PENDING,
    )

    try:
        # Step 2: Upload to blob storage
        upload_to_blob(blob_name, file.file)

        # Step 3: Update DB record -> COMPLETED
        file_record = crud.update_file_status(
            db, file_record.id, FileStatusEnum.COMPLETED
        )

        return {
            "db_id": file_record.id,
            "file_path": file_record.file_path,
            "status": file_record.status,
        }

    except Exception as e:
        # Step 4: Update DB record -> FAILED
        crud.update_file_status(db, file_record.id, FileStatusEnum.FAILED)
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


# for admin only
@router.post("/plant/{plant_id}/bulk-upload")
def bulk_upload(
    plant_id: str,
    request: BulkUploadRequest,
    breeder_id: int = 1,  # admin must specify breeder_id
    db: Session = Depends(get_db),
):
    results = []
    for file in request.files:
        blob_name = f"{uuid.uuid4()}.{file.extension}"
        upload_url = generate_sas_url(blob_name, isUpload=True)

        file_record = crud.create_plant_file(
            db=db,
            plant_id=plant_id,
            date=file.date,
            file_path=blob_name,
            file_type=file.file_type,
            breeder_id=breeder_id,
            status=FileStatusEnum.PENDING,
        )

        results.append(
            {
                "upload_url": upload_url,
                "blob_path": blob_name,
                "db_id": file_record.id,
                "status": file_record.status,
            }
        )
    return results


@router.post("/files/update-status")
def update_file_status(req: StatusUpdateRequest, db: Session = Depends(get_db)):
    db.query(PlantFile).filter(PlantFile.id.in_(req.ids)).update(
        {"status": req.status}, synchronize_session=False
    )
    db.commit()
    return {"updated": len(req.ids)}
