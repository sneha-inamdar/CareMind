# Use official slim Python 3.11 image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Ensure unbuffered logs and prevent .pyc generation
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install runtime system utilities (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy required runtime application code and assets
COPY backend/ ./backend/
COPY src/ ./src/
COPY models/ ./models/
COPY frontend/dist/ ./frontend/dist/
COPY data/demo_waveforms/ ./data/demo_waveforms/
COPY experiments/mimic_multimodal/metrics_summary.json ./experiments/mimic_multimodal/metrics_summary.json

# Expose default port
EXPOSE 8000

# Start Uvicorn dynamically binding to Render's $PORT (fallback to 8000 locally)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
