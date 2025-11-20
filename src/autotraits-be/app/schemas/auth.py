from typing import Optional
from pydantic import EmailStr
from app.schemas.base import BaseSanitizedModel


class UserBase(BaseSanitizedModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    breeder_name: Optional[str] = None  # allow breeder creation at signup
    role: Optional[str] = "user"


class UserInDB(UserBase):
    id: int
    role: str
    breeder_id: int

    model_config = {
        "from_attributes": True,
    }


class Token(BaseSanitizedModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class TokenData(BaseSanitizedModel):
    user_id: int
    breeder_id: Optional[int] = None
    role: Optional[str] = None
    type: Optional[str] = None
