FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir hatchling

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY config/ ./config/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["python", "-m"]
