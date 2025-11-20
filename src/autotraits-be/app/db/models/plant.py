from enum import Enum

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Plant(Base):
    __tablename__ = "plants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    breeder_id = Column(Integer, ForeignKey("breeders.id"), nullable=False)
    plant_code = Column(String, nullable=False)

    breeder = relationship("Breeder", back_populates="plants")
    measurements = relationship(
        "PlantMeasurement", back_populates="plant", cascade="all, delete"
    )
    files = relationship("PlantFile", back_populates="plant", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("breeder_id", "plant_code", name="uix_breeder_plant"),
    )
