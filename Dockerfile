FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY semantic_json/ ./semantic_json/
COPY scripts/        ./scripts/
COPY src/             ./src/

RUN python scripts/build_indices.py

EXPOSE 5000

ENV FLASK_DEBUG=0

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "src.app:_app"]
