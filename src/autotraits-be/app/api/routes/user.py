from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.db.models import User
from app.schemas import UserInDB

router = APIRouter()


# ======= CURRENT USER INFO API =======
@router.get("/me", response_model=UserInDB)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Returns the information of the currently logged-in user
    """
    return current_user
