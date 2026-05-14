FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create the unprivileged user first so COPY --chown works without a separate RUN
RUN useradd -m appuser

WORKDIR /app

# Install deps as root (layer cached independently of source code)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source with ownership set at COPY time — no expensive chown -R afterwards
COPY --chown=appuser:appuser . /app

USER appuser
