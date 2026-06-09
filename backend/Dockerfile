# ==========================================
# Stage 1: Builder (Install dependencies)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies for compiling (GCC, g++...)
# `--no-install-recommends` skips unnecessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runner (Production runtime)
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Optimize Python: Do not write .pyc files and do not buffer log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Update PATH to use the virtual environment from builder
ENV PATH="/opt/venv/bin:$PATH"

# Copy the entire virtual environment (with installed libs) from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY ./app ./app

# Expose API port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
