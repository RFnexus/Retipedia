#!/bin/python3
import os
import re
import json
import sys
import settings
import archives
from libzim.reader import Archive

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(PROJECT_DIR, "zims")

ZIMS_DIR = archives.ZIMS_DIR


def _meta(archive, *keys):
    for key in keys:
        try:
            value = archive.get_metadata(key)
            if value:
                return value.decode("utf-8", "replace").strip()
        except (RuntimeError, KeyError):
            continue
    return ""


def _main_html(archive):
    try:
        if not archive.has_main_entry:
            return "", ""
        item = archive.main_entry.get_item()
        path = item.path
        if not item.mimetype.startswith("text/html"):
            return "", path
        return bytes(item.content).decode("utf-8", "replace"), path
    except Exception:
        return "", ""


def detect_type(archive, html):
    tags = " ".join([_meta(archive, "Tags"), _meta(archive, "Name"),
                     _meta(archive, "Scraper")]).lower()
    if "gutenberg" in tags:
        return "gutenberg"
    video = pdf = total = 0
    try:
        count = min(archive.all_entry_count, 300)
        for i in range(count):
            try:
                mt = archive._get_entry_by_id(i).get_item().mimetype
            except Exception:
                continue
            total += 1
            if "webm" in mt or mt.startswith("video"):
                video += 1
            elif "pdf" in mt:
                pdf += 1
    except Exception:
        pass
    if total and video / total > 0.1:
        return "video"
    if total and pdf / total > 0.1:
        return "pdf"
    if "mw-parser-output" in html:
        return "wikipedia"
    low = html.lower()
    if "http-equiv=\"refresh\"" in low or "http-equiv='refresh'" in low:
        return "spa"
    if html and len(re.sub(r"<[^>]+>", "", html).strip()) < 40:
        return "spa"
    return "generic"


def make_description(archive, html, kind):
    desc = _meta(archive, "Description")
    if desc:
        return desc
    if kind == "wikipedia" and html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for p in soup.find_all("p"):
            text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if len(text) > 40:
                if len(text) > 150:
                    cut = text.rfind(".", 0, 180)
                    text = text[:cut + 1] if cut > 60 else text[:150] + "…"
                return text
    return ""


def build_meta(path):
    archive = Archive(path)
    html, main = _main_html(archive)
    kind = detect_type(archive, html)
    title = _meta(archive, "Title", "Name")
    if not title and html:
        m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
    if not title:
        title = os.path.splitext(os.path.basename(path))[0]
    try:
        count = archive.article_count
    except Exception:
        count = None
    return {
        "title": title,
        "type": kind,
        "description": make_description(archive, html, kind),
        "article_count": count,
        "main_path": main,
    }


def main():
    if not ZIMS_DIR or not os.path.isdir(ZIMS_DIR):
        print("settings.zims_dir is not set to a valid directory")
        return 1
    os.makedirs(META_DIR, exist_ok=True)
    force = "--force" in sys.argv
    names = sorted(f for f in os.listdir(ZIMS_DIR) if f.endswith(".zim"))
    if not names:
        print("No .zim files found in", ZIMS_DIR)
        return 0
    for name in names:
        out = os.path.join(META_DIR, name + ".meta")
        if os.path.exists(out) and not force:
            print("skip (exists):", name)
            continue
        print("scanning:", name)
        try:
            meta = build_meta(os.path.join(ZIMS_DIR, name))
        except Exception as ex:
            print("  failed:", ex)
            continue
        with open(out, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print("  -> {type} | {title} | {article_count} articles".format(**meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
