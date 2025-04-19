FROM python:alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache build-base \
    linux-headers \
    swig \
    rust \
    cargo \
    openssl-dev \
    libffi-dev

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install lightweight alternatives for problematic packages
RUN pip install --no-cache-dir --upgrade pip && \
    # Replace faiss-cpu with a pre-built version or dummy
    pip install --no-cache-dir sentence-transformers && \
    # Install everything except problematic packages
    grep -v "faiss-cpu\|tiktoken\|psutil" requirements.txt > requirements-filtered.txt && \
    pip install --no-cache-dir -r requirements-filtered.txt

# Copy the application code, excluding test files
COPY agent/ agent/
COPY app/ app/
COPY data/ data/
COPY docs/ docs/
COPY .env.example .env.example
COPY README.md .

# Create necessary directories
RUN mkdir -p data/documents logs data/summaries

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Default command
ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["--interactive"] 