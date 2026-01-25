import os
import glob
from datetime import datetime
from flask import current_app
from ..utils import normalize_host

class CookieManager:
    @staticmethod
    def get_cookies_dir():
        return current_app.config['COOKIES_DIR']

    @staticmethod
    def get_cookie_files():
        """Return list of stored cookie files for display."""
        items = []
        cookies_dir = CookieManager.get_cookies_dir()
        try:
            for item_path in glob.glob(os.path.join(cookies_dir, "*.txt")):
                stat = os.stat(item_path)
                items.append({
                    'name': os.path.basename(item_path),
                    'host': os.path.splitext(os.path.basename(item_path))[0],
                    'size': round(stat.st_size / 1024, 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        except OSError as e:
            # In a real app we might log this, but avoiding circular dependencies if logger is separate
            pass
        return sorted(items, key=lambda x: x['modified'], reverse=True)

    @staticmethod
    def save_cookie(file_storage, site_value):
        """Save an uploaded cookie file."""
        host = normalize_host(site_value)
        if not host:
            raise ValueError("Invalid site URL or hostname")
            
        content = file_storage.read()
        if b'Netscape' not in content[:200]:
            raise ValueError("Cookies file must be in Netscape format")
            
        dest_path = os.path.join(CookieManager.get_cookies_dir(), f"{host}.txt")
        with open(dest_path, 'wb') as f:
            f.write(content)
        return host

    @staticmethod
    def delete_cookie(host):
        """Delete a cookie file."""
        safe_host = normalize_host(host)
        if not safe_host:
            raise ValueError("Invalid host")
            
        path = os.path.join(CookieManager.get_cookies_dir(), f"{safe_host}.txt")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
        
    @staticmethod
    def get_cookie_path(host):
        """Get path for a specific host's cookie file."""
        if not host:
            return None
        path = os.path.join(CookieManager.get_cookies_dir(), f"{host}.txt")
        return path if os.path.exists(path) else None

    @staticmethod
    def resolve_cookie_path(url):
        """Resolve cookie path for a URL."""
        host = normalize_host(url)
        return CookieManager.get_cookie_path(host)
