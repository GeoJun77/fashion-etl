# docker/Dockerfile
# Builds the Fashion ETL pipeline image

# Base image — Python 3.11 slim to keep the image lightweight
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for lxml and psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# So pip install only re-runs when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Default command — runs the pipeline once
CMD ["python", "main.py"]