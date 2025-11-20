from datetime import date
import math
from typing import List, Optional

from app.schemas import PlantInDB
from app.schemas.base import BaseSanitizedModel


# ======== FRUIT ========
class FruitBase(BaseSanitizedModel):
    width: Optional[float] = None
    height: Optional[float] = None
    mass: Optional[float] = None


class FruitCreate(FruitBase):
    pass


class FruitInDB(FruitBase):
    id: int

    model_config = {
        "from_attributes": True,
    }


# ======== MEASUREMENT ========
class MeasurementBase(BaseSanitizedModel):
    date: date
    variety: Optional[str] = None
    biomass: Optional[float] = None
    canopy_density: Optional[float] = None
    # ripe: Optional[int] = None
    part_ripe: Optional[int] = None
    unripe: Optional[int] = None
    flower: Optional[int] = None
    yield_per_plant: Optional[float] = None
    cum_yield_per_plant: Optional[float] = None
    class_1: Optional[float] = None
    length_of_cropping: Optional[float] = None
    field: str
    petiole_length: Optional[float] = None
    petiole_strength: Optional[float] = None
    petiole_radius: Optional[float] = None
    truss_length: Optional[float] = None
    truss_strength: Optional[float] = None
    truss_radius: Optional[float] = None
    growth_habit: Optional[str] = None
    fruit_shape: Optional[str] = None
    crop_composition: Optional[float] = None
    plant_height: Optional[float] = None
    exg: Optional[float] = None


class MeasurementCreate(MeasurementBase):
    plant_id: int
    fruits: List[FruitCreate] = []  # allow creating fruits with measurement


class MeasurementUpdate(MeasurementBase):
    fruits: Optional[List[FruitCreate]] = None  # support fruit updates


class MeasurementInDB(MeasurementBase):
    id: int
    ripe: Optional[int] = None
    cumulative_ripe: Optional[int] = None # calculated field on the fly
    plant: PlantInDB
    fruits: List[FruitInDB] = []

    model_config = {
        "from_attributes": True,
    }
