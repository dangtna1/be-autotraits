from app.schemas.base import BaseSanitizedModel


# ======== PLANT ========
class PlantBase(BaseSanitizedModel):
    plant_code: str


class PlantCreate(PlantBase):
    pass


class PlantUpdate(PlantBase):
    pass


class PlantInDB(PlantBase):
    id: int
    model_config = {
        "from_attributes": True,
    }
