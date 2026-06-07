import os
import hashlib

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PROJECT_DIR, "cache")


def _path(zim, entry_path):
    digest = hashlib.sha256(f"{zim}\x00{entry_path}".encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, digest)


def get(zim, entry_path, validator):
    try:
        with open(_path(zim, entry_path), "r", encoding="utf-8") as fh:
            if fh.readline().strip() == str(validator):
                return fh.read()
    except OSError:
        return None
    return None


def put(zim, entry_path, validator, text):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        final = _path(zim, entry_path)
        tmp = f"{final}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(f"{validator}\n")
            fh.write(text)
        os.replace(tmp, final)
    except OSError:
        pass
