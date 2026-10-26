# docker/Dockerfile
# Image shared by the ETL pipeline and the dashboard (see docker-compose.yml)

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first — this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "psycopg2-binary>=2.9,<3"

COPY . .

# Default : run the pipeline now, then every SCHEDULE_HOURS hours
CMD ["python", "main.py", "--schedule"]
