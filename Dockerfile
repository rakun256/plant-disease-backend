FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (psycopg2 ve Pillow için gerekebilir)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render'da dinamik PORT ve DB migration için bash ile başlatalım
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
