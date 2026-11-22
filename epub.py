"""
epub.py - on-demand EPUB extraction for Retipedia.

License: Unlicense (public domain) - see LICENSE.

This software is possible because my parents believed in me and encouraged me to follow my passions.

What it does
------------
Gutenberg .zim archives built by gutenberg2zim with `-f epub` or `-f all`
already contain the EPUB of each book as a regular ZIM entry. So "generating"
an EPUB is really just copying a blob out of the archive - no conversion, no
ebooklib, no pre-building thousands of files.

This module:
  1. finds the EPUB entry for a book inside the .zim
  2. extracts it into NomadNet's storage/files/ folder, where the node can
     serve it over /file/...
  3. keeps that folder under a size budget by evicting least-recently-used
     extractions

If a particular archive turns out to be html-only (no EPUB entries at all),
build_from_html() synthesises a simple single-chapter EPUB from the book's
HTML instead. That path uses only the stdlib plus BeautifulSoup, which
Retipedia already requires - no new dependencies.

Settings (all optional, add to Retipedia's settings.py):

    epub_enabled     = False    # master switch (off by default)
    epub_files_dir   = None     # override NomadNet's storage/files path
    epub_subfolder   = "books"  # subfolder inside storage/files
    epub_cache_mb    = 2048     # size budget for extracted EPUBs
    epub_refresh_min = 1        # must match NomadNet's file_refresh_interval
    epub_fallback    = True     # synthesise an EPUB when the ZIM has none
"""

import hashlib
import json
import os
import re
import subprocess
import time
import unicodedata
import zipfile
from html import escape

import settings
import archives

try:
    from formatting import gutenberg as _gutenberg
except ImportError:  # pragma: no cover - only missing on a non-Retipedia host
    _gutenberg = None

# --------------------------------------------------------------------------
# settings helpers
# --------------------------------------------------------------------------

def _cfg(name, default):
    return getattr(settings, name, default)


def enabled():
    return bool(_cfg("epub_enabled", False))


def refresh_minutes():
    """How long until NomadNet notices a new file. Mirrors the node's
    file_refresh_interval setting - we can't read the node's config from
    here, so it has to be stated in settings.py."""
    try:
        return max(0, int(_cfg("epub_refresh_min", 1)))
    except (TypeError, ValueError):
        return 1


def instant_refresh():
    """True once NomadNet registers new files instantly (for example with
    RetiTap's patch_nomadnet_inotify.py, https://github.com/jwheeler188/RetiTap)
    AND you've confirmed (via
    the node's own log) that it's actually running - see that script's
    verification steps. This is a manual flag, not auto-detected: epub.mu
    runs as a one-shot subprocess with no way to ask the live node process
    whether its file watcher actually started. Defaults to False so a fresh
    install shows the honest "wait ~1 minute" message rather than falsely
    claiming instant delivery."""
    return bool(_cfg("epub_instant_refresh", False))


# --------------------------------------------------------------------------
# locating NomadNet's files directory
# --------------------------------------------------------------------------

def files_root():
    """Return (files_base, books_dir).

    Retipedia lives in <storage>/pages/[subfolder]; NomadNet serves downloads
    from <storage>/files. Walk up from this module to find it.
    """
    override = _cfg("epub_files_dir", None)
    if override:
        base = os.path.expanduser(override)
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        parts = here.split(os.sep)
        if "pages" in parts:
            idx = len(parts) - 1 - parts[::-1].index("pages")
            base = os.path.join(os.sep.join(parts[:idx]), "files")
        else:
            # Unusual layout - fall back to a sibling "files" folder
            base = os.path.join(os.path.dirname(here), "files")

    sub = _cfg("epub_subfolder", "books")
    books = os.path.join(base, sub) if sub else base
    os.makedirs(books, exist_ok=True)
    return base, books


def file_url(filename):
    """The /file/... path a Micron link should point at."""
    sub = _cfg("epub_subfolder", "books")
    return f"/file/{sub}/{filename}" if sub else f"/file/{filename}"


# --------------------------------------------------------------------------
# finding the EPUB entry inside the ZIM
# --------------------------------------------------------------------------
#
# Real Gutenberg ZIMs (as of the 2026 Kiwix builds) store each book's EPUB
# in namespace C, named "<Title as it appears in the ZIM>.<book id>.epub" -
# NOT a fixed "{id}.epub" shape. Guessing a filename per request doesn't
# work here, because the title text (with its exact spaces/punctuation) is
# part of the path.
#
# Instead: run `zimdump list --ns=C` ONCE per archive, pull the trailing
# ".<digits>.epub" off every line to recover the book id, and cache the
# resulting {book_id: exact_path} map to disk. After that, lookups are a
# plain dict hit - no per-request guessing, no per-request shelling out.
#
# A handful of legacy path shapes are kept as a cheap secondary check (some
# older/other ZIM builds really do use "{id}.epub"), and scanning the book's
# own HTML for a download link is the last resort.

_PATH_TEMPLATES = (
    "{id}.epub",
    "{id}.images.epub",
    "{id}.nopic.epub",
    "{id}-images.epub",
    "pg{id}.epub",
    "A/{id}.epub",
    "I/{id}.epub",
    "-/{id}.epub",
)

_HREF_EPUB = re.compile(r"""href\s*=\s*["']([^"']+\.epub)["']""", re.IGNORECASE)
_ID_SUFFIX = re.compile(r"\.(\d+)\.epub$", re.IGNORECASE)


def _try_entry(archive, path):
    try:
        entry = archive.get_entry_by_path(path)
    except (KeyError, RuntimeError):
        return None
    if entry.is_redirect:
        try:
            entry = entry.get_redirect_entry()
        except (KeyError, RuntimeError):
            return None
    return entry


def _is_epub(entry):
    try:
        item = entry.get_item()
    except (KeyError, RuntimeError):
        return False
    return "epub" in (item.mimetype or "").lower() or item.path.lower().endswith(".epub")


def _index_cache_path(zim_path):
    _, books = files_root()
    cache_dir = os.path.dirname(books)  # NomadNet's storage/files
    digest = hashlib.sha1(os.path.abspath(str(zim_path)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(cache_dir, f".epub_index_{digest}.json")


def _list_namespace(zim_path, ns):
    """One-time listing of a ZIM namespace via zimdump. Tries the modern
    subcommand form first, falls back to the older getopt-style flags."""
    attempts = [
        ["zimdump", "list", f"--ns={ns}", str(zim_path)],  # zim-tools >= 3.x
        ["zimdump", "-l", "-n", ns, str(zim_path)],          # older zim-tools
    ]
    last_err = None
    for cmd in attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
            if lines:
                return lines
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            last_err = exc
            continue
    raise RuntimeError(f"Could not list ZIM namespace {ns} with zimdump: {last_err}")


def build_epub_index(zim_path, ns="C", force=False):
    """Return {book_id: exact_path}, building and caching it if needed.

    Cache is invalidated automatically if the ZIM's mtime changes (e.g. you
    swap in a newer archive). Safe to call from multiple concurrent requests:
    each writes to a temp file and renames atomically, so a race just means
    the work happens twice, never a corrupt cache.
    """
    cache_path = _index_cache_path(zim_path)
    try:
        zim_mtime = os.path.getmtime(zim_path)
    except OSError:
        zim_mtime = 0

    if not force:
        try:
            with open(cache_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached.get("zim_mtime") == zim_mtime and cached.get("ns") == ns:
                return cached["index"]
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    index = {}
    for line in _list_namespace(zim_path, ns):
        match = _ID_SUFFIX.search(line)
        if match:
            index[match.group(1)] = line

    tmp = cache_path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"zim_mtime": zim_mtime, "ns": ns, "index": index}, fh)
    os.replace(tmp, cache_path)

    return index


def find_epub_entry(archive, book_id, html=None, entry_path=None, zim_path=None):
    """Return a libzim Entry for the book's EPUB, or None."""
    book_id = str(book_id).strip()

    # Resolve entry_path from book_id using Retipedia's OWN catalog lookup
    # (the "full_by_title.js" index bundled in the ZIM), if we don't already
    # have it. This is exactly how Retipedia itself turns an id back into a
    # path, so it's guaranteed to agree with entry.mu's own navigation, and
    # needs no zimdump / shelling out at all.
    if not entry_path and book_id and _gutenberg is not None:
        try:
            entry_path = _gutenberg.path_for_id(archive, book_id) or None
        except Exception:
            entry_path = None

    # Fastest path, no index needed: these Gutenberg ZIMs pair each book's
    # content entry with an EPUB at the exact same path plus ".epub" - e.g.
    # "Cave Hunting.52424" -> "Cave Hunting.52424.epub".
    if entry_path:
        entry = _try_entry(archive, entry_path + ".epub")
        if entry is not None and _is_epub(entry):
            return entry
        # path_for_id() can resolve to a "<title>_cover.<id>" variant when
        # that's the only entry present; that variant has no epub sibling,
        # so normalize it back to the main path (mirrors gutenberg.book_path)
        # and retry once.
        if _gutenberg is not None:
            normalized = _gutenberg.book_path(entry_path)
            if normalized and normalized != entry_path:
                entry = _try_entry(archive, normalized + ".epub")
                if entry is not None and _is_epub(entry):
                    return entry

    # Fallback for archives without Retipedia's catalog JSON, or where the
    # above didn't resolve: the cached index built from zimdump's C-class
    # listing (see build_epub_index()).
    if zim_path and book_id:
        try:
            index = build_epub_index(zim_path)
        except RuntimeError:
            index = {}
        path = index.get(book_id)
        if path:
            entry = _try_entry(archive, path)
            if entry is not None and _is_epub(entry):
                return entry

    # Secondary: a few legacy path shapes some other ZIM builds do use.
    if book_id:
        for template in _PATH_TEMPLATES:
            entry = _try_entry(archive, template.format(id=book_id))
            if entry is not None and _is_epub(entry):
                return entry

    # Tertiary: whatever the book's own HTML page links to.
    if html:
        base_dir = os.path.dirname(entry_path or "")
        for href in _HREF_EPUB.findall(html):
            href = href.split("#", 1)[0].split("?", 1)[0]
            candidates = [href.lstrip("./")]
            if base_dir:
                candidates.append(os.path.normpath(os.path.join(base_dir, href)))
            for cand in candidates:
                entry = _try_entry(archive, cand)
                if entry is not None and _is_epub(entry):
                    return entry

    return None


# --------------------------------------------------------------------------
# filenames
# --------------------------------------------------------------------------

def slugify(text, max_len=70):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:max_len].strip("-")


def filename_for(book_id, title=None, variant=None):
    slug = slugify(title) if title else ""
    book_id = re.sub(r"[^\w-]", "", str(book_id))
    suffix = f"-{variant}" if variant else ""
    if slug and book_id:
        return f"{slug}-{book_id}{suffix}.epub"
    if slug:
        return f"{slug}{suffix}.epub"
    return f"book-{book_id or 'unknown'}{suffix}.epub"


# --------------------------------------------------------------------------
# cache management
# --------------------------------------------------------------------------

def cache_budget_bytes():
    try:
        return max(0, int(_cfg("epub_cache_mb", 2048))) * 1024 * 1024
    except (TypeError, ValueError):
        return 2048 * 1024 * 1024


def prune_cache(keep=None):
    """Evict least-recently-used EPUBs until the folder fits the budget.

    Returns the number of files removed.
    """
    budget = cache_budget_bytes()
    if budget <= 0:
        return 0

    _, books = files_root()
    entries = []
    total = 0
    for name in os.listdir(books):
        if not name.endswith(".epub"):
            continue
        path = os.path.join(books, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        entries.append((st.st_atime, st.st_size, path, name))
        total += st.st_size

    if total <= budget:
        return 0

    removed = 0
    for _atime, size, path, name in sorted(entries):
        if total <= budget:
            break
        if keep and name == keep:
            continue
        try:
            os.remove(path)
            total -= size
            removed += 1
        except OSError:
            pass
    return removed


def cache_stats():
    _, books = files_root()
    count = 0
    total = 0
    for name in os.listdir(books):
        if name.endswith(".epub"):
            try:
                total += os.path.getsize(os.path.join(books, name))
                count += 1
            except OSError:
                pass
    return count, total


# --------------------------------------------------------------------------
# minimal EPUB builder (fallback for html-only archives)
# --------------------------------------------------------------------------

_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _opf(title, author, book_id):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">retipedia-{escape(str(book_id))}</dc:identifier>
    <dc:title>{escape(title)}</dc:title>
    <dc:creator>{escape(author)}</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>
"""


def _nav(title):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>{escape(title)}</title></head>
<body><nav epub:type="toc"><ol><li><a href="chap1.xhtml">{escape(title)}</a></li></ol></nav></body>
</html>
"""


def _chapter(title, body_html):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{escape(title)}</title><meta charset="utf-8"/></head>
<body><h1>{escape(title)}</h1>
{body_html}
</body>
</html>
"""


def build_from_html(html, title, author, book_id, dest_path):
    """Write a minimal single-chapter EPUB. Stdlib + BeautifulSoup only."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "img", "svg", "iframe"]):
        tag.decompose()
    body = soup.body or soup
    body_html = "".join(str(child) for child in body.children)

    tmp = dest_path + ".part"
    with zipfile.ZipFile(tmp, "w") as zf:
        # The mimetype entry must come first and be stored uncompressed.
        zf.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        zf.writestr("META-INF/container.xml", _CONTAINER_XML, zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", _opf(title, author, book_id), zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/nav.xhtml", _nav(title), zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/chap1.xhtml", _chapter(title, body_html), zipfile.ZIP_DEFLATED)
    os.replace(tmp, dest_path)
    return dest_path


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------

class Result:
    """Outcome of an extraction request."""

    def __init__(self, filename=None, size=0, existed=False, source="zim", error=None):
        self.filename = filename
        self.size = size
        self.existed = existed   # True if it was already extracted before now
        self.source = source     # "zim" or "converted"
        self.error = error

    @property
    def ok(self):
        return self.error is None and self.filename is not None

    @property
    def url(self):
        return file_url(self.filename) if self.filename else None

    @property
    def ready_in(self):
        """Seconds until NomadNet should have registered the file.

        Already-extracted files are assumed registered; a fresh extraction
        normally has to wait for the node's next file scan - unless
        instant_refresh() is set, in which case a NomadNet instant-registration patch
        registers new files within about a second instead.
        """
        if self.existed or instant_refresh():
            return 0
        return refresh_minutes() * 60


def fallback_enabled():
    return bool(_cfg("epub_fallback", True))


def _resolve_book(archive, book_id, entry_path):
    """Resolve entry_path (from book_id via Retipedia's own catalog, if not
    already known) and fetch its HTML if it's a readable page.

    Centralized here so both probe() and extract() see the same resolution
    regardless of whether they were called with a book_id or an entry_path -
    previously this only ran when entry_path was already given, so a
    book_id-only call (e.g. from a bookshelf listing) never got HTML fetched
    at all, breaking the text-only fallback for exactly the case it exists
    for.
    """
    if not entry_path and book_id and _gutenberg is not None:
        try:
            entry_path = _gutenberg.path_for_id(archive, book_id) or None
        except Exception:
            entry_path = None

    html = None
    resolved_path = entry_path
    if entry_path:
        try:
            entry = archive.get_entry_by_path(entry_path)
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
            item = entry.get_item()
            resolved_path = item.path
            if (item.mimetype or "").startswith("text/html"):
                html = bytes(item.content).decode("utf-8", "replace")
        except (KeyError, RuntimeError):
            pass

    return resolved_path, html


class Probe:
    """Cheap, read-only check of what's available for a book - no
    extraction, no writes. Lets epub.mu decide whether there's a genuine
    full-vs-text-only choice to offer before committing to either."""

    def __init__(self, ok=True, error=None, entry_path="", title="",
                 has_full=False, full_size=0):
        self.ok = ok
        self.error = error
        self.entry_path = entry_path
        self.title = title
        self.has_full = has_full
        self.full_size = full_size


def probe(zim, book_id, entry_path=None, title=None):
    """Check what's available for this book without extracting anything."""
    if not enabled():
        return Probe(ok=False, error="EPUB downloads are disabled on this node.")

    try:
        archive = archives.open_archive(zim)
    except FileNotFoundError:
        return Probe(ok=False, error="Archive not found.")

    resolved_path, html = _resolve_book(archive, book_id, entry_path)

    resolved_title = title
    if not resolved_title and resolved_path:
        try:
            entry = archive.get_entry_by_path(resolved_path)
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
            resolved_title = entry.title
        except (KeyError, RuntimeError):
            pass

    full_entry = find_epub_entry(archive, book_id, html=html, entry_path=resolved_path, zim_path=zim)
    full_size = 0
    if full_entry is not None:
        try:
            full_size = full_entry.get_item().size
        except (KeyError, RuntimeError):
            full_entry = None

    return Probe(
        ok=True,
        entry_path=resolved_path or "",
        title=resolved_title or "",
        has_full=full_entry is not None,
        full_size=full_size,
    )


def extract(zim, book_id, title=None, author=None, entry_path=None, variant="auto"):
    """Make sure the requested EPUB variant exists in NomadNet's files folder.

    variant:
      "auto" (default) - prefer the archive's real EPUB; if the archive has
                          none, build a plain text-only one instead. This is
                          the original, pre-variant behavior.
      "full"            - only ever use the archive's real EPUB; error out
                          rather than silently substituting a text build,
                          since the user explicitly asked for the full one.
      "text"            - always build the plain text-only version, even if
                          the archive also has a real EPUB - for clients
                          that can't handle a large illustrated file.
    """
    if not enabled():
        return Result(error="EPUB downloads are disabled on this node.")

    file_variant = "text" if variant == "text" else None
    filename = filename_for(book_id, title, variant=file_variant)
    _, books = files_root()
    dest = os.path.join(books, filename)

    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        try:
            os.utime(dest, None)  # refresh LRU timestamp
        except OSError:
            pass
        return Result(filename, os.path.getsize(dest), existed=True)

    try:
        archive = archives.open_archive(zim)
    except FileNotFoundError:
        return Result(error="Archive not found.")

    resolved_path, html = _resolve_book(archive, book_id, entry_path)

    entry = None
    if variant != "text":
        entry = find_epub_entry(archive, book_id, html=html, entry_path=resolved_path, zim_path=zim)

    if entry is not None:
        try:
            data = bytes(entry.get_item().content)
        except (KeyError, RuntimeError) as exc:
            return Result(error=f"Could not read the EPUB from the archive ({exc}).")
        tmp = dest + ".part"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, dest)
        except OSError as exc:
            return Result(error=f"Could not write the EPUB ({exc}).")
        prune_cache(keep=filename)
        return Result(filename, len(data), existed=False, source="zim")

    if variant == "full":
        return Result(error="This archive does not have a full EPUB for this book.")

    # variant is "auto" with no real EPUB found, or "text" (explicitly forced).
    if variant == "auto" and not fallback_enabled():
        return Result(error="This archive does not contain an EPUB for this book.")
    if not html:
        return Result(error="No EPUB in this archive, and no readable text to build one from.")

    try:
        build_from_html(html, title or f"Book {book_id}", author or "Unknown", book_id, dest)
    except Exception as exc:  # noqa: BLE001 - surface anything to the page
        return Result(error=f"Could not build an EPUB ({exc}).")

    size = os.path.getsize(dest)
    prune_cache(keep=filename)
    return Result(filename, size, existed=False, source="converted")


def human_size(num):
    """Prefer Retipedia's own formatter so sizes match the rest of the site."""
    try:
        from formatting import common
        return common.human_size(num)
    except Exception:  # noqa: BLE001
        num = float(num)
        for unit in ("B", "KB", "MB"):
            if num < 1024:
                return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} GB"
