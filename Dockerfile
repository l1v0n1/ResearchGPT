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
    file-dev

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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