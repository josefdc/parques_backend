# Usa una imagen oficial de Python como base
FROM python:3.11-slim
WORKDIR /app


RUN pip install uv


COPY pyproject.toml uv.lock ./


RUN uv sync
COPY ./app ./app
COPY ./ws ./ws

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]