from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models so their tables are registered in Base.metadata
from app.db.models import breeder, plant, user
