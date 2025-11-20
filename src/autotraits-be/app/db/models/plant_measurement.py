from enum import Enum

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class PlantMeasurement(Base):
    __tablename__ = "plant_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, ForeignKey("plants.id"))
    date = Column(Date)
    variety = Column(String, nullable=True)
    biomass = Column(Float, nullable=True)
    canopy_density = Column(Float, nullable=True)
    ripe = Column(Integer, nullable=True)
    part_ripe = Column(Integer, nullable=True)
    unripe = Column(Integer, nullable=True)
    flower = Column(Integer, nullable=True)
    yield_per_plant = Column(Float, nullable=True)
    cum_yield_per_plant = Column(Float, nullable=True)
    class_1 = Column(Float, nullable=True)
    length_of_cropping = Column(Float, nullable=True)
    field = Column(String)
    petiole_length = Column(Float, nullable=True)
    petiole_strength = Column(Float, nullable=True)
    petiole_radius = Column(Float, nullable=True)
    truss_length = Column(Float, nullable=True)
    truss_strength = Column(Float, nullable=True)
    truss_radius = Column(Float, nullable=True)
    growth_habit = Column(String, nullable=True)
    fruit_shape = Column(String, nullable=True)
    crop_composition = Column(Float, nullable=True)
    plant_height = Column(Float, nullable=True)
    exg = Column(Float, nullable=True)
    fruits = relationship(
        "PlantFruit", back_populates="measurement", cascade="all, delete"
    )
    plant = relationship("Plant", back_populates="measurements")
    __table_args__ = (UniqueConstraint("plant_id", "date", name="uix_plant_date"),)


class PlantFruit(Base):
    __tablename__ = "plant_fruits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    measurement_id = Column(
        Integer, ForeignKey("plant_measurements.id"), nullable=False
    )
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    mass = Column(Float, nullable=True)

    measurement = relationship("PlantMeasurement", back_populates="fruits")
