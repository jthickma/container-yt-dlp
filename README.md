# Media Downloader

A production-ready Docker containerized web application for downloading media content using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [gallery-dl](https://github.com/mikf/gallery-dl).

## Features

- **Web-based UI**: Simple and intuitive interface for downloading media
- **Video Downloads**: Support for YouTube and 1000+ video sites via yt-dlp
- **Gallery Downloads**: Support for Instagram, Twitter/X, Reddit, Pinterest, and many image/gallery sites via gallery-dl
- **File Management**: View, download, and delete downloaded media files
- **Production Ready**: Multi-stage Docker build with security best practices
- **Health Checks**: Built-in health check endpoints for container orchestration

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/jthickma/container-yt-dlp.git
cd container-yt-dlp

# Start the service
docker compose up -d

# Access the web UI
open http://localhost:5000
```

### Using Docker

```bash
# Build the image
docker build -t media-downloader .

# Run the container
docker run -d \
  --name media-downloader \
  -p 5000:5000 \
  -v media-downloads:/app/downloads \
  media-downloader
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment mode |
| `SECRET_KEY` | (auto-generated) | Flask secret key for sessions |
| `DOWNLOAD_DIR` | `/app/downloads` | Directory for downloaded files |
| `MAX_DOWNLOAD_TIMEOUT` | `300` | Download timeout in seconds |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `5000` | Server port |

### Persistent Storage

Downloads are stored in `/app/downloads` inside the container. Mount a volume to persist downloads:

```bash
# Docker
docker run -v /path/to/downloads:/app/downloads media-downloader

# Docker Compose (uses named volume by default)
docker compose up -d
```

## Supported Sites

### Video Sites (via yt-dlp)
- YouTube
- Vimeo
- Twitch
- TikTok
- And [1000+ more sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### Gallery Sites (via gallery-dl)
- Instagram
- Twitter/X
- Reddit
- Pinterest
- Imgur
- Flickr
- DeviantArt
- Tumblr
- VSCO
- And [many more](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Display main page with download form |
| `/` | POST | Submit a URL for download |
| `/download/<filename>` | GET | Download a file (or ZIP for directories) |
| `/delete/<filename>` | POST | Delete a file or directory |
| `/health` | GET | Health check endpoint |

## Development

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
FLASK_ENV=development python app.py
```

### Project Structure

```
.
├── app.py              # Main Flask application
├── Dockerfile          # Multi-stage production Docker build
├── docker-compose.yml  # Docker Compose configuration
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Web UI template
└── .env.example        # Example environment configuration
```

## Security

This application implements several security best practices:

- **Non-root user**: Container runs as unprivileged user
- **Read-only filesystem**: Root filesystem is read-only
- **Input sanitization**: All user inputs are sanitized
- **Resource limits**: CPU and memory limits configured
- **Health checks**: Container health monitoring
- **No new privileges**: Prevents privilege escalation

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
