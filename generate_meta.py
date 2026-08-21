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


def validate_interpreter(value):
    if not value:
        return "no interpreter given"
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return "interpreter contains control characters"
    parts = value.split()
    if len(parts) > 2:
        return "a shebang can pass at most one argument (e.g. '/usr/bin/env python3')"
    exe = parts[0]
    if not os.path.isabs(exe):
        return "'{0}' is not an absolute path".format(exe)
    if not os.path.isfile(exe):
        return "'{0}' does not exist".format(exe)
    if not os.access(exe, os.X_OK):
        return "'{0}' is not executable".format(exe)
    if len(value) + 2 > 127:
        return "shebang longer than 127 characters may be truncated by the kernel"
    return None


def fix_shebangs(interpreter):

    error = validate_interpreter(interpreter)
    if error:
        print("Refusing to rewrite shebangs:", error)
        return 1
    shebang = "#!" + interpreter + "\n"
    for name in sorted(os.listdir(PROJECT_DIR)):
        if not name.endswith(".mu"):
            continue
        path = os.path.join(PROJECT_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines or not lines[0].startswith("#!"):
            print("skip (no shebang):", name)
            continue
        mode = os.stat(path).st_mode | 0o111
        if lines[0] != shebang:
            lines[0] = shebang
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.writelines(lines)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
            
            print("  -> {0} now uses {1}".format(name, interpreter))
        else:
            os.chmod(path, mode)

            print("ok:", name)
    return 0


def main():
    for arg in sys.argv[1:]:
        if arg == "--fix-shebangs":
            return fix_shebangs(sys.executable)
        if arg.startswith("--fix-shebangs="):
            return fix_shebangs(arg.split("=", 1)[1])
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
