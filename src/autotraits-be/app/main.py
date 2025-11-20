from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, plants, root, user, plant_measurements, plant_images

origins = [
    "http://localhost:5173",
    "https://autotraits-frontend.onrender.com",  # prod frontend here
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # For public access, or specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root.router, tags=["Root"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user.router, prefix="/api/user", tags=["User API"])
app.include_router(plants.router, prefix="/api", tags=["Plant API"])
app.include_router(plant_measurements.router, prefix="/api", tags=["Plant Measurements API"])
app.include_router(plant_images.router, prefix="/api", tags=["Plant Images API"])
