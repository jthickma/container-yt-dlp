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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024  # 16KB max request size

# Download configuration
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/app/downloads')
DOWNLOAD_TIMEOUT = int(os.environ.get('MAX_DOWNLOAD_TIMEOUT', '300'))

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    logger.info(f"Created download directory: {DOWNLOAD_DIR}")


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
            return render_template('index.html', error="Please provide a valid URL", files=files)
        
        logger.info(f"Download request received for URL: {url[:50]}...")
        
        try:
            if is_gallery_url(url):
                # Use subprocess to call gallery-dl CLI
                gallery_dl_path = find_executable('gallery-dl')
                logger.info(f"Using gallery-dl at: {gallery_dl_path}")
                result = subprocess.run(
                    [
                        gallery_dl_path,
                        "--directory", DOWNLOAD_DIR,
                        "--quiet",
                        url
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=DOWNLOAD_TIMEOUT
                )
                message = 'Gallery download completed!'
                logger.info(f"Gallery download completed for URL: {url[:50]}...")
            else:
                ydl_opts = {
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s-%(id)s.%(ext)s'),
                    'noplaylist': True,
                    'format': 'best[height<=720]',  # Limit quality to reduce size
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                message = 'Video download completed!'
                logger.info(f"Video download completed for URL: {url[:50]}...")
            
            files = get_downloaded_files()
            return render_template('index.html', message=message, files=files)
        except subprocess.TimeoutExpired:
            logger.warning(f"Download timed out for URL: {url[:50]}...")
            files = get_downloaded_files()
            return render_template('index.html', error="Download timed out. Please try again.", files=files)
        except subprocess.CalledProcessError as e:
            error_msg = f"gallery-dl error: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            logger.error(f"Gallery-dl error: {error_msg}")
            files = get_downloaded_files()
            return render_template('index.html', error=error_msg, files=files)
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download error: {str(e)}")
            files = get_downloaded_files()
            return render_template('index.html', error=f"Download error: {str(e)}", files=files)
        except Exception as e:
            logger.exception(f"Unexpected error during download: {str(e)}")
            files = get_downloaded_files()
            return render_template('index.html', error=f"An error occurred: {str(e)}", files=files)
    
    files = get_downloaded_files()
    return render_template('index.html', error=None, message=None, files=files)

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
            return render_template('index.html', error="File or directory not found", files=files)
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        files = get_downloaded_files()
        return render_template('index.html', error=f"Error deleting item: {str(e)}", files=files)


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
