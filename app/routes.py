from flask import Blueprint, render_template, request, send_from_directory, redirect, url_for, current_app
import subprocess
import logging
import yt_dlp
from .services.downloader import Downloader
from .services.file_manager import FileManager
from .services.cookie_manager import CookieManager

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    error = None
    message = None
    
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        selected_cookie = request.form.get('cookie_file')
        
        if not url:
            error = "Please provide a valid URL"
        else:
            logger.info(f"Download request for URL: {url[:50]}... with cookie: {selected_cookie}")
            try:
                if Downloader.is_gallery_url(url):
                    Downloader.download_gallery(url, selected_cookie)
                    message = 'Gallery download completed!'
                else:
                    Downloader.download_video(url, selected_cookie)
                    message = 'Video download completed!'
            except subprocess.TimeoutExpired:
                error = "Download timed out. Please try again."
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.strip() if e.stderr else ''
                if '403' in stderr:
                    error = "Access denied (403). Try selecting a specific cookie file."
                else:
                    error = f"Gallery-dl error: {stderr or 'Unknown error'}"
            except yt_dlp.utils.DownloadError as e:
                error = f"Download error: {str(e)}"
            except Exception as e:
                logger.exception("Unexpected error")
                error = f"An error occurred: {str(e)}"

    return render_template('index.html', 
                         error=error, 
                         message=message, 
                         files=FileManager.list_files(), 
                         cookie_files=CookieManager.get_cookie_files())

@main_bp.route('/download/<path:filename>')
def download_file(filename):
    path_or_dir, name, mime = FileManager.prepare_download(filename)
    if not path_or_dir:
        return "File not found", 404
    
    return send_from_directory(path_or_dir, name, as_attachment=True, mimetype=mime)

@main_bp.route('/delete/<path:filename>', methods=['POST'])
def delete_item(filename):
    if FileManager.delete_item(filename):
        return redirect(url_for('main.index'))
    return render_template('index.html', 
                         error="File not found", 
                         files=FileManager.list_files(), 
                         cookie_files=CookieManager.get_cookie_files())

@main_bp.route('/cookies/upload', methods=['POST'])
def upload_cookies():
    site_value = request.form.get('site', '').strip()
    if 'cookies_file' not in request.files:
        return render_template('index.html', error="No file selected", files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())
        
    try:
        host = CookieManager.save_cookie(request.files['cookies_file'], site_value)
        return render_template('index.html', message=f"Cookies uploaded for {host}", files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())
    except ValueError as e:
        return render_template('index.html', error=str(e), files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())
    except Exception as e:
        return render_template('index.html', error=f"Error saving cookies: {str(e)}", files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())

@main_bp.route('/cookies/delete/<path:host>', methods=['POST'])
def delete_cookies(host):
    try:
        if CookieManager.delete_cookie(host):
            return redirect(url_for('main.index'))
        return render_template('index.html', error="Cookie file not found", files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())
    except Exception as e:
        return render_template('index.html', error=str(e), files=FileManager.list_files(), cookie_files=CookieManager.get_cookie_files())

@main_bp.route('/health')
def health_check():
    return {'status': 'healthy'}, 200
