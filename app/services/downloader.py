import os
import subprocess
import logging
import shlex
import yt_dlp
from flask import current_app
from ..utils import find_executable
from .cookie_manager import CookieManager

logger = logging.getLogger(__name__)

class Downloader:
    @staticmethod
    def is_gallery_url(url):
        import re
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

    @staticmethod
    def download_gallery(url, selected_cookie_file=None):
        gallery_dl_path = find_executable('gallery-dl')
        download_dir = current_app.config['DOWNLOAD_DIR']
        
        # Determine cookies path: explicit selection -> auto-resolve -> configured default
        cookies_path = None
        if selected_cookie_file:
             cookies_path = CookieManager.get_cookie_path(selected_cookie_file)
        
        if not cookies_path:
             cookies_path = CookieManager.resolve_cookie_path(url)
        
        cmd = [
            gallery_dl_path,
            "--directory", download_dir,
            "--quiet",
            "--user-agent", current_app.config['USER_AGENT'],
        ]
        
        if cookies_path:
            cmd.extend(["--cookies", cookies_path])
            
        extra_args = current_app.config.get('GALLERY_DL_EXTRA_ARGS')
        if extra_args:
            cmd.extend(shlex.split(extra_args))
            
        cmd.append(url)
        
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=current_app.config['DOWNLOAD_TIMEOUT']
        )

    @staticmethod
    def download_video(url, selected_cookie_file=None):
        # Determine cookies path
        cookies_path = None
        if selected_cookie_file:
             cookies_path = CookieManager.get_cookie_path(selected_cookie_file)
        
        if not cookies_path:
             cookies_path = CookieManager.resolve_cookie_path(url)

        def get_opts(format_str):
            opts = {
                'outtmpl': os.path.join(current_app.config['DOWNLOAD_DIR'], '%(title)s-%(id)s.%(ext)s'),
                'noplaylist': True,
                'format': format_str,
                'format_sort': ['res:720', 'ext:mp4:m4a'],
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'retries': 3,
                'fragment_retries': 3,
                'socket_timeout': 30,
                'concurrent_fragment_downloads': 3,
                'http_headers': {
                    'User-Agent': current_app.config['USER_AGENT'],
                },
            }
            if cookies_path:
                opts['cookiefile'] = cookies_path
            return opts

        # Try with preferred format
        chosen_format = current_app.config['YTDLP_FORMAT']
        if current_app.config.get('YTDLP_MAX_HEIGHT'):
            try:
                max_height = int(current_app.config['YTDLP_MAX_HEIGHT'])
                chosen_format = (
                    f"bestvideo[height<={max_height}]+bestaudio/"
                    f"best[height<={max_height}]/best"
                )
            except ValueError:
                pass

        try:
            with yt_dlp.YoutubeDL(get_opts(chosen_format)) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            if "Requested format is not available" in str(e):
                # Fallback to 'best'
                with yt_dlp.YoutubeDL(get_opts('best')) as ydl:
                    ydl.download([url])
            else:
                raise
