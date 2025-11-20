from pydantic import BaseModel, validator
import math

class BaseSanitizedModel(BaseModel):
    @validator("*", pre=True)
    def sanitize_floats(cls, v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
