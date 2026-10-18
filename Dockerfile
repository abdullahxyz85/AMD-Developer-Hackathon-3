FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libcairo2-dev libpango1.0-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-tutor.txt .
RUN pip install --no-cache-dir -r requirements-tutor.txt

COPY recommendation ./recommendation
COPY RAG ./RAG
COPY server ./server
COPY tutor ./tutor

ENV PYTHONPATH=/app:/app/RAG
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8080}"]