FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY evals ./evals

# Persistent data lives here (mount a volume in production).
ENV UPLOAD_DIR=/data/uploads \
    DB_PATH=/data/analyses.db
RUN mkdir -p /data/uploads

EXPOSE 8000

# Honor $PORT if the platform provides one (Railway, Cloud Run, ...).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
