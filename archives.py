import os
import json
import settings
from libzim.reader import Archive

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(PROJECT_DIR, "zims")

ZIMS_DIR = getattr(settings, "zims_dir", None)
SINGLE_PATH = getattr(settings, "archive_path", None)
SINGLE_TYPE = getattr(settings, "archive_type", "wikipedia")


def meta_path(name):
    return os.path.join(META_DIR, os.path.basename(name) + ".meta")


def has_meta(name):
    return os.path.isfile(meta_path(name))


def load_meta(name):
    try:
        with open(meta_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def zim_path(name):
    name = os.path.basename(name or "")
    if not name.endswith(".zim"):
        raise ValueError("invalid archive name")
    if ZIMS_DIR:
        candidate = os.path.join(ZIMS_DIR, name)
        if os.path.isfile(candidate):
            return candidate
    if SINGLE_PATH and name == os.path.basename(SINGLE_PATH):
        return SINGLE_PATH
    raise FileNotFoundError(name)


def zim_names():
    names = []
    if ZIMS_DIR and os.path.isdir(ZIMS_DIR):
        names = sorted(f for f in os.listdir(ZIMS_DIR) if f.endswith(".zim"))
    if not names and SINGLE_PATH:
        names = [os.path.basename(SINGLE_PATH)]
    return names


def available_names():
    names = [n for n in zim_names() if has_meta(n)]
    if not names and SINGLE_PATH:
        names = [os.path.basename(SINGLE_PATH)]
    return names


def archive_type(name):
    meta = load_meta(name)
    if meta.get("type"):
        return meta["type"]
    if SINGLE_PATH and name == os.path.basename(SINGLE_PATH):
        return SINGLE_TYPE
    return "generic"


def list_archives():
    items = []
    for name in available_names():
        meta = load_meta(name)
        items.append({
            "name": name,
            "title": meta.get("title") or name,
            "type": meta.get("type") or archive_type(name),
            "description": meta.get("description", ""),
            "article_count": meta.get("article_count"),
            "main_path": meta.get("main_path", ""),
        })
    return items


def open_archive(name):
    return Archive(zim_path(name))


def main_path(name, archive=None):
    meta = load_meta(name)
    if meta.get("main_path"):
        return meta["main_path"]
    archive = archive or open_archive(name)
    try:
        if archive.has_main_entry:
            return archive.main_entry.get_item().path
    except Exception:
        pass
    return ""
