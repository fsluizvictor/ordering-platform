FROM python:3.12-slim

WORKDIR /app

# Copy dependency spec first so this layer is cached across source-only changes.
COPY pyproject.toml ./

# Install production dependencies (no dev extras).
RUN pip install --no-cache-dir \
    "flask>=3.0,<4" \
    "gunicorn>=23,<24" \
    "python-dotenv>=1.0,<2"

# Copy shared utilities and service source.
COPY shared/ ./shared/
COPY core-api/src/ ./core-api/src/

# shared/ is importable as a top-level package; core_api is under src/.
ENV PYTHONPATH=/app/core-api/src:/app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["python", "-m", "core_api.main"]
