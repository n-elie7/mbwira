FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install dependencies first so this layer is cached between builds
COPY backend/requirements.txt /code/backend/requirements.txt
RUN pip install --no-cache-dir -r /code/backend/requirements.txt

COPY backend/app /code/backend/app
COPY frontend /code/frontend

WORKDIR /code/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
