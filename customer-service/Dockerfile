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
    "python-dotenv>=1.0,<2"

# Copy shared utilities and service source.
COPY shared/ ./shared/
COPY customer-service/src/ ./customer-service/src/

# shared/ is importable as a top-level package; customer_service is under src/.
ENV PYTHONPATH=/app/customer-service/src:/app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8001

CMD ["python", "-m", "customer_service.main"]
