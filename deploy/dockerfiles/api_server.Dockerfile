FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY api_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared_common and api_server code
COPY shared_common /shared_common
COPY api_server /app

# Set PYTHONPATH to include shared_common and api_server
ENV PYTHONPATH=/app:/shared_common

CMD ["python", "run.py"]
