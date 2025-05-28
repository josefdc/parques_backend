# Usa una imagen oficial de Python como base
FROM python:3.11-slim@sha256:40a026f39ace9b8e75bca7835d3dd91fd977bb259f878c9572f8cbd8541ca952


WORKDIR /app


RUN pip install uv


COPY pyproject.toml uv.lock ./


RUN uv sync
COPY ./app ./app
COPY ./ws ./ws

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]