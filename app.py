from flask import Flask, request, render_template, redirect, url_for
import yt_dlp
import os

app = Flask(__name__)
DOWNLOAD_DIR = '/app/downloads' #  Important: Match the volume mount in podman-compose.yml

# Ensure the download directory exists.  IMPORTANT
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

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
            return render_template('index.html', message='Download started!') # Add messages for more feedback
        except yt_dlp.utils.DownloadError as e:
            return render_template('index.html', error=str(e))
        except Exception as e:
            return render_template('index.html', error=f"An unexpected error occurred: {str(e)}")
    return render_template('index.html', error=None, message=None)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Debug mode, accessible from outside the container