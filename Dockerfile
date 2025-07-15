FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir yt-dlp flask gallery-dl

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Create downloads directory
RUN mkdir -p /app/downloads

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]

