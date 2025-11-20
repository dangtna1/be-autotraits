# AutoTraits Backend

## Overview

This backend service for AutoTraits is built with FastAPI. It provides RESTful APIs for authentication, plant data management, user management, and core business logic with traits images (2D, 3D) stored on Azure Blob Storage (ADLS Gen 2). The backend uses SQLAlchemy for ORM and Alembic for migrations!

## Folder Structure

- `app/`
  - `api/routes/`: API endpoints (`auth.py`, `plants.py`, `root.py`, `user.py`)
  - `core/`: Core logic (ADLS integration, config, security)
  - `crud/`: CRUD operations for plant data
  - `db/`: Database models and session management
  - `schemas/`: Pydantic schemas for request/response validation
  - `main.py`: FastAPI app entry point
  - `dependencies.py`: Dependency injection for routes.

## Features

- JWT-based authentication
- CRUD operations for plant records
- User registration and profile management
- Integration with Azure Data Lake Storage (ADLS)
- Database migrations with Alembic

## Setup

1. **Install dependencies**
    ```bash
    pip install -r requirements.txt

2. **Configure environment**
- Edit app/core/conf.py for environment variables and secrets.
- Database settings in alembic.ini and app/db/session.py.

3. **Run migrations**
    ```bash
    alembic revision --autogenerate -m "<migration message>"
    alembic upgrade head
4. **Start the server locally**
    ```bash
    uvicorn app.main:app --reload

## API Endpoints

- /auth/ — Authentication (login, register)
- /plants/ — Plant data CRUD
- /user/ — User profile
- / — Root endpoint (health check)

##  Development

- Tests: Located in tests/
- Seeding scripts: See scripts/ for data import utilities
    - Seeding traits attributes: ```python scripts/seed_2d_traits.py scripts/2d_traits_per_IDDate\ 1.csv```
    - Seeding traits images: ```python scripts/seed_plant_images.py scripts/traits_2d_images.csv```
    - Similar for 3D data

## Run with Docker

- Build the docker (stand at /autotraits-be):
    ```docker build -t autotraits-be .```
- Run the program with the docker image above:
    ```docker run -p 8000:10000 --env-file .env autotraits-be```