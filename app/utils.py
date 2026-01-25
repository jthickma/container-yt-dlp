import os
import re
import shutil
from urllib.parse import urlparse

def find_executable(name):
    """Find the full path to an executable."""
    return shutil.which(name) or name

def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal attacks."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename

def normalize_host(value):
    """Normalize a hostname or URL into a safe hostname string."""
    if not value:
        return None
    if re.match(r'^https?://', value):
        parsed = urlparse(value)
        host = parsed.netloc
    else:
        host = value
    if ':' in host:
        host = host.split(':', 1)[0]
    host = host.strip().lower()
    host = re.sub(r'[^a-z0-9.-]', '', host)
    return host or None
