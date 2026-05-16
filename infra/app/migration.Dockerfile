FROM python:3.12-slim

WORKDIR /workspace

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "alembic", "upgrade", "head"]
