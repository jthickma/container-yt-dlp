from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import yt_dlp
import gallery_dl
import os
import glob
from datetime import datetime
import re
import shutil

app = Flask(__name__)
DOWNLOAD_DIR = '/app/downloads'

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

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
        r'https?://(www\.)?pinterest\.com',
        r'https?://imgur\.com',
        r'https?://(www\.)?reddit\.com/r/',
        # Add other gallery-dl supported sites as needed
    ]
    return any(re.match(pattern, url) for pattern in gallery_patterns)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        try:
            if is_gallery_url(url):
                gallery_dl.main(['--directory', DOWNLOAD_DIR, url])
                message = 'Gallery download completed!'
            else:
                ydl_opts = {
                    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s-%(id)s.%(ext)s'),
                    'noplaylist': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                message = 'Video download completed!'
            
            files = get_downloaded_files()
            return render_template('index.html', message=message, files=files)
        except Exception as e:
            files = get_downloaded_files()
            return render_template('index.html', error=f"An error occurred: {str(e)}", files=files)
    
    files = get_downloaded_files()
    return render_template('index.html', error=None, message=None, files=files)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve downloaded files or directories to users"""
    path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.isdir(path):
        # For directories, consider creating a zip file for download
        # For simplicity, this is not implemented here.
        return "Directory downloads are not yet supported.", 400
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route('/delete/<path:filename>', methods=['POST'])
def delete_item(filename):
    """Delete a downloaded file or directory"""
    try:
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