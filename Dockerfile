FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    cmake \
    libffi-dev \
    openssl-dev \
    bzip2-dev \
    jpeg-dev \
    zlib-dev \
    swig \
    pcre-dev \
    file-dev \
    openblas-dev \
    openblas \
    lapack-dev \
    g++ \
    gfortran

# Copy requirements and wheelhouse directory
COPY requirements.txt .
COPY wheelhouse wheelhouse

# Install dependencies - first try to use pre-built wheel for faiss-cpu
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -d "wheelhouse" ] && [ "$(ls -A wheelhouse 2>/dev/null)" ]; then \
        echo "Using pre-built wheels in wheelhouse" && \
        pip install --no-cache-dir wheelhouse/*.whl && \
        grep -v "faiss-cpu" requirements.txt > requirements-without-faiss.txt && \
        pip install --no-cache-dir -r requirements-without-faiss.txt; \
    else \
        echo "Building from source" && \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Create necessary directories first
RUN mkdir -p data/documents/vector_store data/summaries logs

# Copy the application code
COPY agent/ agent/
COPY app/ app/
COPY docs/ docs/
COPY .env.example .env.example
COPY README.md .

# Ensure data directories exist
# This is a redundant step to ensure the directories are created
# even if the COPY steps fail due to missing directories
RUN mkdir -p data/documents/vector_store data/summaries logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Default command
ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["--interactive"] 