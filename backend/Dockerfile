FROM python:3.12-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (layer cache optimization)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source code
COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
