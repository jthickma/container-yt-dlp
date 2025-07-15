# app.py

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
import urllib.parse
import shutil
import sys

app = Flask(__name__)

# Use /app/downloads in Docker, downloads in local development
if os.path.exists('/app'):
    DOWNLOAD_DIR = '/app/downloads'
else:
    DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')

def find_executable(name):
    """Find the full path to an executable"""
    return shutil.which(name) or name

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal attacks"""
    # Remove any directory separators and resolve to just the filename
    filename = os.path.basename(filename)
    # Remove any dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename

def get_downloaded_files():
    """Get list of downloaded files and directories with metadata"""
    items = []
    for item_path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        stat = os.stat(item_path)
        items.append({
            'name': os.path.basename(item_path),
            'size': round(stat.st_size / (1024*1024), 2),  # Size in MB
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'is_dir': os.path.isdir(item_path)
        })
    return sorted(items, key=lambda x: x['modified'], reverse=True)

def is_gallery_url(url):
    """Check if a URL is likely a gallery URL"""
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
        # Add other gallery-dl supported sites as needed
    ]
    return any(re.match(pattern, url) for pattern in gallery_patterns)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            files = get_downloaded_files()
            return render_template('index.html', error="Please provide a valid URL", files=files)
        
        try:
            if is_gallery_url(url):
                # Use subprocess to call gallery-dl CLI with dynamically found path
                gallery_dl_path = find_executable('gallery-dl')
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
                    timeout=300  # 5 minute timeout
                )
                message = 'Gallery download completed!'
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
            
            files = get_downloaded_files()
            return render_template('index.html', message=message, files=files)
        except subprocess.TimeoutExpired:
            files = get_downloaded_files()
            return render_template('index.html', error="Download timed out. Please try again.", files=files)
        except subprocess.CalledProcessError as e:
            files = get_downloaded_files()
            error_msg = f"gallery-dl error: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            return render_template('index.html', error=error_msg, files=files)
        except yt_dlp.utils.DownloadError as e:
            files = get_downloaded_files()
            return render_template('index.html', error=f"Download error: {str(e)}", files=files)
        except Exception as e:
            files = get_downloaded_files()
            return render_template('index.html', error=f"An error occurred: {str(e)}", files=files)
    
    files = get_downloaded_files()
    return render_template('index.html', error=None, message=None, files=files)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve downloaded files or directories to users"""
    # Sanitize the filename to prevent directory traversal
    filename = sanitize_filename(filename)
    path = os.path.join(DOWNLOAD_DIR, filename)
    
    if not os.path.exists(path):
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
            
            return send_from_directory(temp_dir, f"{filename}.zip", as_attachment=True, 
                                     mimetype='application/zip')
        except Exception as e:
            return f"Error creating zip file: {str(e)}", 500
    else:
        # For regular files, detect mime type
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True, 
                                 mimetype=mime_type)

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_item(filename):
    """Delete a downloaded file or directory"""
    try:
        # Sanitize the filename to prevent directory traversal
        filename = sanitize_filename(filename)
        path = os.path.join(DOWNLOAD_DIR, filename)
        
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return redirect(url_for('index'))
        else:
            files = get_downloaded_files()
            return render_template('index.html', error="File or directory not found", files=files)
    except Exception as e:
        files = get_downloaded_files()
        return render_template('index.html', error=f"Error deleting item: {str(e)}", files=files)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
