import os
import glob
import shutil
import zipfile
import tempfile
import mimetypes
from datetime import datetime
from flask import current_app, send_from_directory
from ..utils import sanitize_filename

class FileManager:
    @staticmethod
    def get_download_dir():
        return current_app.config['DOWNLOAD_DIR']

    @staticmethod
    def list_files():
        """Get list of downloaded files."""
        items = []
        download_dir = FileManager.get_download_dir()
        try:
            for item_path in glob.glob(os.path.join(download_dir, "*")):
                stat = os.stat(item_path)
                items.append({
                    'name': os.path.basename(item_path),
                    'size': round(stat.st_size / (1024*1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_dir': os.path.isdir(item_path)
                })
        except OSError:
            pass
        return sorted(items, key=lambda x: x['modified'], reverse=True)

    @staticmethod
    def delete_item(filename):
        """Delete a file or directory."""
        filename = sanitize_filename(filename)
        path = os.path.join(FileManager.get_download_dir(), filename)
        
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        return False

    @staticmethod
    def prepare_download(filename):
        """Prepare a file for download (zipping directories if needed)."""
        filename = sanitize_filename(filename)
        download_dir = FileManager.get_download_dir()
        path = os.path.join(download_dir, filename)
        
        if not os.path.exists(path):
            return None, None, None

        if os.path.isdir(path):
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, f"{filename}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, path)
                        zipf.write(file_path, arcname)
            return temp_dir, f"{filename}.zip", 'application/zip'
        else:
            mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            return download_dir, filename, mime_type
