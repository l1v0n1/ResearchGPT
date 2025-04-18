FROM python:alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache build-base

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data/documents logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["--interactive"] 