import os
import re
import hashlib
import settings
import archives
from formatting.common import resolve_path, clean_label

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(PROJECT_DIR, "images")
EXTENSIONS = {"image/webp": "webp", "WEBP": "webp", "image/png": "png", "image/jpeg": "jpg",
              "image/gif": "gif"}
MAX_BYTES = 256 * 1024

_URL_RE = re.compile(r"`:/media/(?:[^`\s)]*/)?images/([^`\s)]+)\)")
_archives = {}


def _archive(zim):
    if zim not in _archives:
        _archives[zim] = archives.open_archive(zim)
    return _archives[zim]


def materialize(zim, entry_path):
    if not zim or not entry_path or not getattr(settings, "images", False):
        return ""
    try:
        entry = _archive(zim).get_entry_by_path(entry_path)
        if entry.is_redirect:
            entry = entry.get_redirect_entry()
        item = entry.get_item()
    except (KeyError, FileNotFoundError, RuntimeError):
        return ""
    ext = EXTENSIONS.get(item.mimetype)
    if not ext or item.size > MAX_BYTES:
        return ""
    folder = os.path.splitext(zim)[0]
    name = hashlib.sha256(entry_path.encode("utf-8")).hexdigest()[:24] + "." + ext
    target = os.path.join(IMAGE_DIR, folder, name)
    if not os.path.isfile(target):
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = f"{target}.{os.getpid()}.tmp"
            with open(tmp, "wb") as fh:
                fh.write(bytes(item.content))
            os.replace(tmp, target)
        except OSError:
            return ""
    rf = archives.root_folder()
    return f":/media/{rf}/images/{folder}/{name}" if rf else f":/media/images/{folder}/{name}"


def missing(text):
    return any(not os.path.isfile(os.path.join(IMAGE_DIR, rel)) for rel in _URL_RE.findall(text or ""))


def image_tag(src, alt, ctx, width="n", align="c"):
    url = materialize(ctx.get("zim"), resolve_path(src, ctx))
    if not url:
        return ""
    label = clean_label(alt).replace(")", "")
    return f"`({label}`w={width}`a={align}`{url})"
