# app/schemas/common.py
from typing import Generic, List, TypeVar
from app.schemas.base import BaseSanitizedModel

T = TypeVar("T")


class PaginatedResponse(BaseSanitizedModel, Generic[T]):
    total: int
    offset: int
    limit: int
    items: List[T]
