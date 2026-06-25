FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates ./templates

# Port can be overridden via the FRONTEND_PORT env var (set in .env / compose).
ENV FRONTEND_PORT=27432

EXPOSE ${FRONTEND_PORT}

CMD ["sh", "-c", "gunicorn app:app --workers 2 --bind 0.0.0.0:${FRONTEND_PORT}"]
