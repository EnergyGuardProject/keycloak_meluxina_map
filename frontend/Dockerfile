FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates ./templates

EXPOSE 27432

CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:27432"]
