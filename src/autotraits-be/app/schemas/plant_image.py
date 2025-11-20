from datetime import date
from enum import Enum
from typing import List, Optional
from app.schemas.base import BaseSanitizedModel


# ======== FILE ========
class FileTypeEnum(str, Enum):
    TWO_D = "TWO_D"
    THREE_D = "THREE_D"


class FileStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileIn(BaseSanitizedModel):
    date: Optional[str]
    file_type: str
    extension: str


class BulkUploadRequest(BaseSanitizedModel):
    files: List[FileIn]


class StatusUpdateRequest(BaseSanitizedModel):
    ids: List[int]
    status: FileStatusEnum


class FileBase(BaseSanitizedModel):
    plant_id: str
    date: date
    file_path: str
    file_type: FileTypeEnum
    file_status: FileStatusEnum = FileStatusEnum.PENDING


class FileCreate(FileBase):
    pass


class FileInDB(FileBase):
    id: int

    model_config = {
        "from_attributes": True,
    }
