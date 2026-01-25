import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    MAX_CONTENT_LENGTH = 512 * 1024  # 512KB max request size
    
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
    
    # Optional default cookie file (legacy support)
    COOKIE_FILE = os.environ.get('COOKIE_FILE')
    
    GALLERY_DL_EXTRA_ARGS = os.environ.get('GALLERY_DL_EXTRA_ARGS', '')

    @staticmethod
    def init_app(app):
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(Config.COOKIES_DIR, exist_ok=True)
