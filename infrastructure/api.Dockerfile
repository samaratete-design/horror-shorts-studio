FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY packages ./packages
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api ./apps/api
COPY alembic ./alembic
COPY alembic.ini .

ENV PYTHONPATH=/app/apps/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api"]
