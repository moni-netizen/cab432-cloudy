FROM python:3.14-slim

WORKDIR /app

RUN useradd --create-home --shell bin/bash appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_tools.py .

USER appuser

CMD ["python", "-u", "mcp_tools.py"]