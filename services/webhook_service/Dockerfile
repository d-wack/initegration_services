# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements first (for better caching)
COPY shared/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy shared modules
COPY shared /app/shared/

# Copy service code
COPY services/webhook_service /app/service/

# Expose port
EXPOSE 8000

# Set Python path to include shared modules
ENV PYTHONPATH=/app

# Run the service
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"] 