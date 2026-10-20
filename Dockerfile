FROM python:3.11-slim

# Install system dependencies (curl is required for the healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, seeds, reports, and logs
COPY src/ ./src/
COPY seeds/ ./seeds/
COPY reports/ ./reports/
COPY logs/ ./logs/

# Expose API port 8080
EXPOSE 8080

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    API_PORT=8080 \
    DATABASE_URL=postgresql://ledger:ledger@ledger:5432/ledger

# Run the FastAPI application via uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
