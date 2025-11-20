# Use an official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies (for psycopg2, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Expose port
EXPOSE 10000

# Use Gunicorn with multiple Uvicorn workers for concurrency
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--workers", "3", "--bind", "0.0.0.0:10000", "app.main:app"]

