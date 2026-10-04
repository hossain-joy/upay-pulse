FROM python:3.11-slim

WORKDIR /app

# Install system deps. libgomp1 is required by scikit-learn / lightgbm wheels
# at runtime; build-essential + libpq-dev are needed for psycopg2-binary
# fallback builds. curl is for Render health checks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
# Pin numpy<2 during pip install to keep lightgbm/scikit-learn pre-built
# wheels happy (manylinux2014 wheels are not yet numpy-2 compatible).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir 'numpy<2' && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY ml /app/ml
COPY scripts /app/scripts
COPY data /app/data

ENV PYTHONPATH=/app

EXPOSE 8000

# init_db and seed_baseline are best-effort: if they fail (e.g., transient DB
# connection issue during Render cold-start), we still want uvicorn to come up
# so the deploy doesn't get marked failed. They can be re-run manually.
CMD sh -c 'python scripts/init_db.py || echo "[WARN] init_db failed, continuing"; \
           python scripts/seed_baseline.py || echo "[WARN] seed_baseline failed, continuing"; \
           exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}'
