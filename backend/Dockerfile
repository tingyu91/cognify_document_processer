FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (layer caching)
COPY pyproject.toml .
RUN uv sync --no-dev

# Copy application code
COPY . .

# Run migrations then start the API
CMD uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
