from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import yt_dlp
import os
import glob
from datetime import datetime

app = Flask(__name__)
DOWNLOAD_DIR = '/app/downloads' #  Important: Match the volume mount in podman-compose.yml

# Ensure the download directory exists.  IMPORTANT
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_downloaded_files():
    """Get list of downloaded files with metadata"""
    files = []
    for file_path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                'name': os.path.basename(file_path),
                'size': round(stat.st_size / (1024*1024), 2),  # Size in MB
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    return sorted(files, key=lambda x: x['modified'], reverse=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        try:
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s-%(id)s.%(ext)s'), # Save to the shared directory
                'noplaylist': True, # Disable playlist downloads for simplicity.  Remove if needed.
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            files = get_downloaded_files()
            return render_template('index.html', message='Download completed!', files=files)
        except yt_dlp.utils.DownloadError as e:
            files = get_downloaded_files()
            return render_template('index.html', error=str(e), files=files)
        except Exception as e:
            files = get_downloaded_files()
            return render_template('index.html', error=f"An unexpected error occurred: {str(e)}", files=files)
    
    files = get_downloaded_files()
    return render_template('index.html', error=None, message=None, files=files)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve downloaded files to users"""
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """Delete a downloaded file"""
    try:
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return redirect(url_for('index'))
        else:
            files = get_downloaded_files()
            return render_template('index.html', error="File not found", files=files)
    except Exception as e:
        files = get_downloaded_files()
        return render_template('index.html', error=f"Error deleting file: {str(e)}", files=files)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Debug mode, accessible from outside the container