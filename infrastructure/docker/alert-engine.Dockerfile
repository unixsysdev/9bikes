# Alert Engine Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
COPY src/monitors_mcp src/monitors_mcp/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Add health check endpoints
COPY docker/alert-engine-health.py /app/health_server.py

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose health check port
EXPOSE 8080

# Run alert engine with health server
CMD ["python", "-c", "import asyncio; from src.monitors_mcp.alert_engine import AlertEngine; from health_server import HealthServer; asyncio.run(asyncio.gather(AlertEngine().start(), HealthServer().start()))"]
