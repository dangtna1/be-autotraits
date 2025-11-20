from enum import Enum

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class FileTypeEnum(str, Enum):
    TWO_D = "TWO_D"
    THREE_D = "THREE_D"


class FileStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PlantFile(Base):
    __tablename__ = "plant_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, ForeignKey("plants.id"))
    date = Column(Date)
    file_path = Column(String)
    file_type = Column(SqlEnum(FileTypeEnum), nullable=False)
    status = Column(SqlEnum(FileStatusEnum), default=FileStatusEnum.PENDING)
    plant = relationship("Plant", back_populates="files")
