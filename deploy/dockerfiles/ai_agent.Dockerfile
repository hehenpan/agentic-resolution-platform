FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared_common and ai_agent configurations to support setup
COPY shared_common /shared_common

# Copy ai_agent pyproject.toml first to install dependencies
COPY ai_agent/pyproject.toml /app/pyproject.toml
COPY ai_agent/src /app/src

# Install python package dependencies using pip
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir langgraph-cli[inmem]

# Copy remaining code
COPY ai_agent /app

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app:/

# Start LangGraph server
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024"]
