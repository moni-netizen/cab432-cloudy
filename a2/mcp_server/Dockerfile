FROM python:3.13-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY github_access.py .

USER appuser

EXPOSE 8000

CMD ["python", "-u", "github_access.py"]