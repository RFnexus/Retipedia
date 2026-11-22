#!/usr/bin/env python3
"""
check_zim_epubs.py - does this Gutenberg .zim actually contain EPUBs?

License: Unlicense (public domain) - see LICENSE.

This software is possible because my parents believed in me and encouraged me to follow my passions.

Run this FIRST. Everything else depends on the answer.

    python3 check_zim_epubs.py /path/to/gutenberg_en_all_2026-01.zim
    python3 check_zim_epubs.py /path/to/archive.zim 1342 84 11

With book IDs, it reports the exact entry path each EPUB was found at, which
tells you which naming layout your archive uses. Without them, it samples
random entries looking for anything with an EPUB mimetype.

Only needs libzim, which Retipedia already requires.
"""

import sys

from libzim.reader import Archive

TEMPLATES = (
    "{id}.epub",
    "{id}.images.epub",
    "{id}.nopic.epub",
    "{id}-images.epub",
    "pg{id}.epub",
    "A/{id}.epub",
    "I/{id}.epub",
    "-/{id}.epub",
)


def probe(archive, book_id):
    for template in TEMPLATES:
        path = template.format(id=book_id)
        try:
            entry = archive.get_entry_by_path(path)
        except (KeyError, RuntimeError):
            continue
        if entry.is_redirect:
            try:
                entry = entry.get_redirect_entry()
            except (KeyError, RuntimeError):
                continue
        item = entry.get_item()
        mt = (item.mimetype or "").lower()
        if "epub" in mt or item.path.lower().endswith(".epub"):
            return path, item.path, item.size, item.mimetype
    return None


def sample(archive, tries=400):
    """Look for EPUB entries by pulling random entries out of the archive."""
    found = []
    for _ in range(tries):
        try:
            entry = archive.get_random_entry()
        except (KeyError, RuntimeError):
            break
        if entry.is_redirect:
            continue
        try:
            item = entry.get_item()
        except (KeyError, RuntimeError):
            continue
        mt = (item.mimetype or "").lower()
        if "epub" in mt or item.path.lower().endswith(".epub"):
            found.append((item.path, item.size, item.mimetype))
            if len(found) >= 5:
                break
    return found


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    zim_path = sys.argv[1]
    book_ids = sys.argv[2:]

    if book_ids and book_ids[0] == "--build-index":
        # Pre-warm epub.py's real {book_id: exact_path} cache, so the first
        # actual download request doesn't pay the zimdump cost.
        import epub
        index = epub.build_epub_index(zim_path, force=True)
        print(f"Indexed {len(index)} EPUB(s) from namespace C.")
        for book_id in book_ids[1:]:
            hit = index.get(book_id)
            print(f"  {book_id}: {hit if hit else 'NOT in index'}")
        return

    archive = Archive(zim_path)
    print(f"archive:       {zim_path}")
    print(f"all entries:   {archive.all_entry_count:,}")
    print(f"articles:      {archive.article_count:,}")
    print(f"media entries: {archive.media_count:,}")
    print()

    if book_ids:
        for book_id in book_ids:
            hit = probe(archive, book_id)
            if hit:
                tried, real, size, mimetype = hit
                print(f"book {book_id}: FOUND")
                print(f"  matched template : {tried}")
                print(f"  actual entry path: {real}")
                print(f"  size             : {size:,} bytes")
                print(f"  mimetype         : {mimetype}")
            else:
                print(f"book {book_id}: no EPUB found at any known path")
            print()
        return

    print("Sampling random entries for EPUBs...")
    found = sample(archive)
    if found:
        print(f"Found {len(found)} EPUB entr(ies) - this archive has EPUBs:")
        for path, size, mimetype in found:
            print(f"  {path}  ({size:,} bytes, {mimetype})")
        print()
        print("Note the path layout above - if it doesn't match one of the")
        print("templates in epub.py, add it to _PATH_TEMPLATES there.")
    else:
        print("No EPUBs turned up in the sample.")
        print("That may mean this archive is html-only (built without -f epub),")
        print("or just that the sample missed them. Re-run with specific book")
        print("IDs, e.g.:  python3 check_zim_epubs.py archive.zim 1342 84 11")
        print()
        print("If the archive really has none, set epub_fallback = True in")
        print("settings.py and EPUBs will be built from the text instead.")


if __name__ == "__main__":
    main()
