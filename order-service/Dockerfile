FROM python:3.12-slim

WORKDIR /app

# Copy dependency spec first so this layer is cached across source-only changes.
COPY pyproject.toml ./

# Install production dependencies (no dev extras).
RUN pip install --no-cache-dir \
    "flask>=3.0,<4" \
    "gunicorn>=23,<24" \
    "sqlalchemy>=2.0,<3" \
    "psycopg2-binary>=2.9,<3" \
    "pika>=1.3,<2" \
    "python-dotenv>=1.0,<2"

# Copy shared utilities and service source.
COPY shared/ ./shared/
COPY order-service/src/ ./order-service/src/

# shared/ is importable as a top-level package; order_service is under src/.
ENV PYTHONPATH=/app/order-service/src:/app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8003

CMD ["python", "-m", "order_service.main"]
