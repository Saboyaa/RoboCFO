FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install runtime dependencies only
RUN uv sync --no-dev --frozen

# Application code + frozen contracts
COPY backend/app/ app/
COPY contracts.py contracts.py

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
