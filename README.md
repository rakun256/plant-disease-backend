# Plant Disease Classifier Backend

Flutter mobil uygulaması için geliştirilmiş, Apple Leaf (Elma Yaprağı) hastalıklarını tespit eden (Healthy, Rust, Scab) FastAPI tabanlı backend.

## Kurulum
1. `python3 -m venv venv` ve `source venv/bin/activate` ile sanal ortam oluşturun.
2. `pip install -r requirements.txt` komutuyla bağımlılıkları yükleyin.
3. `.env.example` dosyasını `.env` olarak kopyalayarak veritabanı değişkenlerini ayarlayın.
4. `alembic init alembic` ve ardından migration dosyalarınızı oluşturarak `alembic upgrade head` ile veritabanını güncelleyin.
5. `uvicorn app.main:app --reload` ile projeyi başlatın.
6. `http://localhost:8000/docs` üzerinden Swagger arayüzüne erişebilirsiniz.

## Docker ile Kurulum
`docker-compose up --build` komutunu çalıştırarak veritabanı ve API'yi anında ayağa kaldırabilirsiniz.
