# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./

ARG PYTHON_EXTRAS=ml

RUN --mount=type=cache,target=/root/.cache/pip \
    printf '# ReviewRAG\n' > README.md \
    && pip install --upgrade pip \
    && if [ -n "$PYTHON_EXTRAS" ]; then pip install ".[$PYTHON_EXTRAS]"; else pip install "."; fi

COPY README.md ./
COPY app ./app
COPY data ./data
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
