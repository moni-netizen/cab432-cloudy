FROM python:3.13-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY page_ingestion.py .

USER appuser

CMD ["python", "-u", "page_ingestion.py"]