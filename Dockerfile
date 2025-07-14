FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install yt-dlp flask gallery-dl

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]

