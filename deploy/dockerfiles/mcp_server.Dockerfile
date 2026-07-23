FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared_common first
COPY shared_common /shared_common

# Copy mcp_server pyproject.toml first to install dependencies
COPY mcp_server/pyproject.toml /app/pyproject.toml
COPY mcp_server/README.md /app/README.md
COPY mcp_server/src /app/src

# Install python package dependencies using pip
RUN pip install --no-cache-dir -e .

# Copy remaining code
COPY mcp_server /app

# Set PYTHONPATH
ENV PYTHONPATH=/app/src:/app:/

CMD ["python", "src/main.py"]
