FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY ml /app/ml
COPY scripts /app/scripts
COPY data /app/data

ENV PYTHONPATH=/app

EXPOSE 8000

CMD python scripts/init_db.py && python scripts/seed_baseline.py && \
    uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
