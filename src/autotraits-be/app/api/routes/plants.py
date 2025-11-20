from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import app.crud as crud
from app.db.models import Role, User
from app.dependencies import get_db, get_current_user
from app.schemas import PlantInDB, PlantCreate, PlantUpdate, PaginatedResponse

router = APIRouter()


# ========== PLANTS ==========
@router.post("/plants", response_model=PlantInDB)
def create_plant_route(
    plant: PlantCreate,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        # Admin can assign plant to any breeder explicitly
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id required for admin")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot create plant for other breeder"
            )
        final_breeder_id = current_user.breeder_id
    return crud.create_plant(db, plant, breeder_id=final_breeder_id)


@router.get("/plants", response_model=PaginatedResponse[PlantInDB])
def list_plants_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        total, items = crud.get_all_plants(db, offset=offset, limit=limit)
    else:
        total, items = crud.get_all_plants(
            db, current_user.breeder_id, offset=offset, limit=limit
        )
    return {"total": total, "offset": offset, "limit": limit, "items": items}


@router.get("/plants/{plant_id}", response_model=PlantInDB)
def get_plant_route(
    plant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        return crud.get_plant(db, plant_id)
    else:
        return crud.get_plant(db, plant_id, current_user.breeder_id)


@router.put("/plants/{plant_id}", response_model=PlantInDB)
def update_plant_route(
    plant_id: int,
    plant: PlantUpdate,
    breeder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        if not breeder_id:
            raise HTTPException(status_code=400, detail="breeder_id required for admin")
        final_breeder_id = breeder_id
    else:
        if breeder_id and breeder_id != current_user.breeder_id:
            raise HTTPException(
                status_code=403, detail="Cannot update plant for other breeder"
            )
        final_breeder_id = current_user.breeder_id

    return crud.update_plant(db, plant_id, plant, breeder_id=final_breeder_id)


# @router.get("/plants/code/{plant_code}", response_model=PlantInDB)
# def get_plant_by_code_route(
#     plant_code: str,
#     breeder_id: Optional[int] = None,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     if current_user.role == Role.ADMIN:
#         # Admin can retrieve plant for any breeder explicitly
#         if not breeder_id:
#             raise HTTPException(status_code=400, detail="breeder_id required for admin")
#         final_breeder_id = breeder_id
#     else:
#         if breeder_id and breeder_id != current_user.breeder_id:
#             raise HTTPException(
#                 status_code=403, detail="Cannot retrieve plant for other breeder"
#             )
#         final_breeder_id = current_user.breeder_id

#     plant = crud.get_plant_by_code(db, plant_code, final_breeder_id)
#     return plant


@router.delete("/plants/{plant_id}", response_model=PlantInDB)
def delete_plant_by_id_route(
    plant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == Role.ADMIN:
        return crud.delete_plant(db, plant_id)
    else:
        return crud.delete_plant(db, plant_id, current_user.breeder_id)


# @router.delete("/plants/code/{plant_code}", response_model=PlantInDB)
# def delete_plant_by_code_route(
#     plant_code: str,
#     breeder_id: Optional[int] = None,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     if current_user.role == Role.ADMIN:
#         # Admin can assign plant to any breeder explicitly
#         if not breeder_id:
#             raise HTTPException(status_code=400, detail="breeder_id required for admin")
#         final_breeder_id = breeder_id
#     else:
#         if breeder_id and breeder_id != current_user.breeder_id:
#             raise HTTPException(
#                 status_code=403, detail="Cannot delete plant for other breeder"
#             )
#         final_breeder_id = current_user.breeder_id

#     return crud.delete_plant_by_code(db, plant_code, final_breeder_id)
