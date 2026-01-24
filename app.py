# app.py
"""
Media Downloader Web Application

A Flask-based web UI for downloading media content using yt-dlp and gallery-dl.
Supports videos from YouTube and media from various gallery sites.
"""

from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import yt_dlp
import os
import glob
from datetime import datetime
import re
import shutil
import subprocess
import zipfile
import tempfile
import mimetypes
import logging
import secrets
import shlex
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024  # 512KB max request size

# Download configuration
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/app/downloads')
DOWNLOAD_TIMEOUT = int(os.environ.get('MAX_DOWNLOAD_TIMEOUT', '300'))
COOKIES_DIR = os.environ.get('COOKIES_DIR', '/app/cookies')
USER_AGENT = os.environ.get(
    'USER_AGENT',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
YTDLP_FORMAT = os.environ.get('YTDLP_FORMAT', 'bestvideo*+bestaudio/best')
YTDLP_MAX_HEIGHT = os.environ.get('YTDLP_MAX_HEIGHT')
COOKIES_PATH = os.environ.get('COOKIES_PATH')
YTDLP_COOKIES = os.environ.get('YTDLP_COOKIES')
GALLERY_DL_COOKIES = os.environ.get('GALLERY_DL_COOKIES')
GALLERY_DL_EXTRA_ARGS = os.environ.get('GALLERY_DL_EXTRA_ARGS', '')

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    logger.info(f"Created download directory: {DOWNLOAD_DIR}")

# Ensure cookies directory exists
if not os.path.exists(COOKIES_DIR):
    os.makedirs(COOKIES_DIR, exist_ok=True)
    logger.info(f"Created cookies directory: {COOKIES_DIR}")


def find_executable(name):
    """Find the full path to an executable."""
    return shutil.which(name) or name


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal attacks.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        A safe filename string
    """
    # Remove any directory separators and resolve to just the filename
    filename = os.path.basename(filename)
    # Remove any dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename


def normalize_host(value):
    """Normalize a hostname or URL into a safe hostname string."""
    if not value:
        return None
    if re.match(r'^https?://', value):
        parsed = urlparse(value)
        host = parsed.netloc
    else:
        host = value
    if ':' in host:
        host = host.split(':', 1)[0]
    host = host.strip().lower()
    host = re.sub(r'[^a-z0-9.-]', '', host)
    return host or None


def cookies_path_for_host(host):
    """Return the cookies file path for a specific host if it exists."""
    if not host:
        return None
    candidate = os.path.join(COOKIES_DIR, f"{host}.txt")
    if os.path.exists(candidate):
        return candidate
    return None


def cookies_path_for_url(url):
    """Return the cookies file path for a URL's host if it exists."""
    host = normalize_host(url)
    return cookies_path_for_host(host)


def resolve_cookies_path(path):
    """Return a cookies path if it exists, otherwise None with a warning."""
    if not path:
        return None
    if os.path.exists(path):
        return path
    logger.warning(f"Cookies file not found at: {path}")
    return None


def build_gallery_dl_command(url):
    """Build the gallery-dl command with common headers and optional cookies."""
    gallery_dl_path = find_executable('gallery-dl')
    cookies_path = (
        cookies_path_for_url(url)
        or resolve_cookies_path(GALLERY_DL_COOKIES)
        or resolve_cookies_path(COOKIES_PATH)
    )
    cmd = [
        gallery_dl_path,
        "--directory", DOWNLOAD_DIR,
        "--quiet",
        "--user-agent", USER_AGENT,
    ]
    if cookies_path:
        cmd.extend(["--cookies", cookies_path])
    if GALLERY_DL_EXTRA_ARGS:
        cmd.extend(shlex.split(GALLERY_DL_EXTRA_ARGS))
    cmd.append(url)
    logger.info(f"Using gallery-dl at: {gallery_dl_path}")
    return cmd


def build_yt_dlp_opts(url, use_fallback_format=False):
    """Build yt-dlp options with resilient defaults and optional cookies."""
    cookies_path = (
        cookies_path_for_url(url)
        or resolve_cookies_path(YTDLP_COOKIES)
        or resolve_cookies_path(COOKIES_PATH)
    )
    if use_fallback_format:
        chosen_format = 'best'
    elif YTDLP_MAX_HEIGHT:
        try:
            max_height = int(YTDLP_MAX_HEIGHT)
            chosen_format = (
                f"bestvideo[height<={max_height}]+bestaudio/"
                f"best[height<={max_height}]/best"
            )
        except ValueError:
            logger.warning("Invalid YTDLP_MAX_HEIGHT; falling back to default format")
            chosen_format = YTDLP_FORMAT
    else:
        chosen_format = YTDLP_FORMAT

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s-%(id)s.%(ext)s'),
        'noplaylist': True,
        'format': chosen_format,
        'format_sort': ['res:720', 'ext:mp4:m4a'],
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 30,
        'concurrent_fragment_downloads': 3,
        'http_headers': {
            'User-Agent': USER_AGENT,
        },
    }
    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
    return ydl_opts


def get_cookie_files():
    """Return list of stored cookie files for display."""
    items = []
    try:
        for item_path in glob.glob(os.path.join(COOKIES_DIR, "*.txt")):
            stat = os.stat(item_path)
            items.append({
                'name': os.path.basename(item_path),
                'host': os.path.splitext(os.path.basename(item_path))[0],
                'size': round(stat.st_size / 1024, 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    except OSError as e:
        logger.error(f"Error reading cookies directory: {e}")
    return sorted(items, key=lambda x: x['modified'], reverse=True)

def get_downloaded_files():
    """
    Get list of downloaded files and directories with metadata.
    
    Returns:
        List of dictionaries containing file information, sorted by modification time.
    """
    items = []
    try:
        for item_path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
            stat = os.stat(item_path)
            items.append({
                'name': os.path.basename(item_path),
                'size': round(stat.st_size / (1024*1024), 2),  # Size in MB
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'is_dir': os.path.isdir(item_path)
            })
    except OSError as e:
        logger.error(f"Error reading download directory: {e}")
    return sorted(items, key=lambda x: x['modified'], reverse=True)

def is_gallery_url(url):
    """
    Check if a URL is likely a gallery URL that should use gallery-dl.
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL matches a known gallery site pattern
    """
    gallery_patterns = [
        r'https?://(www\.)?instagram\.com',
        r'https?://(www\.)?twitter\.com',
        r'https?://(x\.)?twitter\.com',
        r'https?://(www\.)?pinterest\.com',
        r'https?://imgur\.com',
        r'https?://(www\.)?reddit\.com/r/',
        r'https?://(www\.)?vsco\.co',
        r'https?://(www\.)?flickr\.com',
        r'https?://(www\.)?deviantart\.com',
        r'https?://(www\.)?tumblr\.com'
    ]
    return any(re.match(pattern, url) for pattern in gallery_patterns)

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main page handler for the media downloader.
    
    GET: Display the download form and list of downloaded files.
    POST: Process a download request for the submitted URL.
    """
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error="Please provide a valid URL", files=files, cookie_files=cookie_files)
        
        logger.info(f"Download request received for URL: {url[:50]}...")
        
        try:
            if is_gallery_url(url):
                # Use subprocess to call gallery-dl CLI
                cmd = build_gallery_dl_command(url)
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=DOWNLOAD_TIMEOUT
                )
                message = 'Gallery download completed!'
                logger.info(f"Gallery download completed for URL: {url[:50]}...")
            else:
                ydl_opts = build_yt_dlp_opts(url)
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    if "Requested format is not available" in str(e):
                        logger.warning("Requested format not available; retrying with fallback format")
                        fallback_opts = build_yt_dlp_opts(url, use_fallback_format=True)
                        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                            ydl.download([url])
                    else:
                        raise
                message = 'Video download completed!'
                logger.info(f"Video download completed for URL: {url[:50]}...")
            
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', message=message, files=files, cookie_files=cookie_files)
        except subprocess.TimeoutExpired:
            logger.warning(f"Download timed out for URL: {url[:50]}...")
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error="Download timed out. Please try again.", files=files, cookie_files=cookie_files)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ''
            if '403' in stderr and not resolve_cookies_path(GALLERY_DL_COOKIES):
                error_msg = (
                    "gallery-dl error: Access denied (403). This site may require "
                    "cookies. Configure GALLERY_DL_COOKIES or COOKIES_PATH."
                )
            else:
                error_msg = f"gallery-dl error: {stderr or 'Unknown error'}"
            logger.error(f"Gallery-dl error: {error_msg}")
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error=error_msg, files=files, cookie_files=cookie_files)
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download error: {str(e)}")
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error=f"Download error: {str(e)}", files=files, cookie_files=cookie_files)
        except Exception as e:
            logger.exception(f"Unexpected error during download: {str(e)}")
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error=f"An error occurred: {str(e)}", files=files, cookie_files=cookie_files)
    
    files = get_downloaded_files()
    cookie_files = get_cookie_files()
    return render_template('index.html', error=None, message=None, files=files, cookie_files=cookie_files)

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Serve downloaded files or directories to users.
    
    For directories, creates a ZIP archive on-the-fly.
    For files, serves them directly with appropriate MIME type.
    
    Args:
        filename: The name of the file or directory to download
    """
    # Sanitize the filename to prevent directory traversal
    filename = sanitize_filename(filename)
    path = os.path.join(DOWNLOAD_DIR, filename)
    
    if not os.path.exists(path):
        logger.warning(f"File not found: {filename}")
        return "File not found", 404
    
    if os.path.isdir(path):
        # Create a temporary zip file for the directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{filename}.zip")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, path)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Created ZIP archive for directory: {filename}")
            return send_from_directory(temp_dir, f"{filename}.zip", as_attachment=True, 
                                     mimetype='application/zip')
        except Exception as e:
            logger.error(f"Error creating zip file: {str(e)}")
            return f"Error creating zip file: {str(e)}", 500
    else:
        # For regular files, detect mime type
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        logger.info(f"Serving file: {filename}")
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True, 
                                 mimetype=mime_type)

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_item(filename):
    """
    Delete a downloaded file or directory.
    
    Args:
        filename: The name of the file or directory to delete
    """
    try:
        # Sanitize the filename to prevent directory traversal
        filename = sanitize_filename(filename)
        path = os.path.join(DOWNLOAD_DIR, filename)
        
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Deleted directory: {filename}")
            else:
                os.remove(path)
                logger.info(f"Deleted file: {filename}")
            return redirect(url_for('index'))
        else:
            logger.warning(f"File or directory not found for deletion: {filename}")
            files = get_downloaded_files()
            cookie_files = get_cookie_files()
            return render_template('index.html', error="File or directory not found", files=files, cookie_files=cookie_files)
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error=f"Error deleting item: {str(e)}", files=files, cookie_files=cookie_files)


@app.route('/cookies/upload', methods=['POST'])
def upload_cookies():
    """Upload a Netscape-format cookies file for a specific site."""
    site_value = request.form.get('site', '').strip()
    host = normalize_host(site_value)
    if not host:
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Please provide a valid site URL or hostname.", files=files, cookie_files=cookie_files)

    if 'cookies_file' not in request.files:
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Please choose a cookies file to upload.", files=files, cookie_files=cookie_files)

    upload = request.files['cookies_file']
    if not upload or upload.filename == '':
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Please choose a cookies file to upload.", files=files, cookie_files=cookie_files)

    content = upload.read()
    if b'Netscape' not in content[:200]:
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Cookies file must be in Netscape format.", files=files, cookie_files=cookie_files)

    dest_path = os.path.join(COOKIES_DIR, f"{host}.txt")
    try:
        with open(dest_path, 'wb') as f:
            f.write(content)
        logger.info(f"Uploaded cookies for host: {host}")
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', message=f"Cookies uploaded for {host}.", files=files, cookie_files=cookie_files)
    except Exception as e:
        logger.error(f"Error saving cookies: {str(e)}")
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error=f"Error saving cookies: {str(e)}", files=files, cookie_files=cookie_files)


@app.route('/cookies/delete/<path:host>', methods=['POST'])
def delete_cookies(host):
    """Delete a stored cookies file by host."""
    safe_host = normalize_host(host)
    if not safe_host:
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Invalid cookies entry.", files=files, cookie_files=cookie_files)

    path = os.path.join(COOKIES_DIR, f"{safe_host}.txt")
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Deleted cookies for host: {safe_host}")
            return redirect(url_for('index'))
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error="Cookies file not found.", files=files, cookie_files=cookie_files)
    except Exception as e:
        logger.error(f"Error deleting cookies: {str(e)}")
        files = get_downloaded_files()
        cookie_files = get_cookie_files()
        return render_template('index.html', error=f"Error deleting cookies: {str(e)}", files=files, cookie_files=cookie_files)


@app.route('/health')
def health_check():
    """Health check endpoint for container orchestration."""
    return {'status': 'healthy'}, 200


if __name__ == '__main__':
    # Development server - use gunicorn in production
    debug_mode = os.environ.get('FLASK_ENV', 'production') != 'production'
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    
    logger.info(f"Starting Media Downloader on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)
