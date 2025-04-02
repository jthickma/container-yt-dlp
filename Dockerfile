FROM python:3.11-slim

# Install dependencies (yt-dlp and any webserver - e.g., Flask).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install yt-dlp flask

# Set working directory
WORKDIR /app

# Copy your web app code (assuming it's in the current directory)
COPY . /app

# Expose the port (if the web app listens on a specific port - e.g., 5000)
EXPOSE 5000  
#Adjust the port if your web app uses a different one

# Command to run the web app
CMD ["python", "app.py"] #  Replace with your app's execution command
