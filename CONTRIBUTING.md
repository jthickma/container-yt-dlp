# Contributing to Media Downloader

Thank you for your interest in contributing to Media Downloader! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or later
- Docker and Docker Compose (for containerized development)
- ffmpeg (for video processing)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/jthickma/container-yt-dlp.git
   cd container-yt-dlp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the development server:
   ```bash
   FLASK_ENV=development python app.py
   ```

### Docker Development

Build and run using Docker Compose:

```bash
docker compose up --build
```

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test your changes thoroughly
5. Commit with clear, descriptive messages
6. Push to your fork
7. Submit a Pull Request

## Pull Request Guidelines

- Describe what your changes do and why
- Reference any related issues
- Ensure the Docker build succeeds
- Update documentation if needed

## Reporting Issues

When reporting issues, please include:

- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs or error messages

## Questions?

Feel free to open an issue for any questions or discussions about the project.
