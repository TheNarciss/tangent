FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copie le code SOURCE AVANT le pip install -e (pip install -e en mode editable
# a besoin de trouver le package "app" déjà présent)
COPY pyproject.toml ./
COPY app/ ./app/
COPY config/ ./config/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Alembic migrations (alembic.ini + alembic/ requis par init_db.py au startup)
COPY alembic.ini ./
COPY alembic/ ./alembic/

RUN mkdir -p /app/data

# Create non-root user for runtime (security: avoid root in container)
RUN useradd -u 1000 -m -s /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
