#!/usr/bin/env python3
"""
clean_epubs.py - clear out EPUBs that were extracted on demand.

License: Unlicense (public domain) - see LICENSE.

This software is possible because my parents believed in me and encouraged me to follow my passions.

Mirrors Retipedia's clean_images.py.

    python3 clean_epubs.py          remove every extracted EPUB
    python3 clean_epubs.py 30       remove only EPUBs untouched for 30+ days
    python3 clean_epubs.py --stats  just report what's there
"""

import os
import sys
import time

import epub


def main():
    args = [a for a in sys.argv[1:]]
    _, books = epub.files_root()

    count, total = epub.cache_stats()
    print(f"{books}")
    print(f"{count} EPUB(s), {epub.human_size(total)}")

    if "--stats" in args:
        return

    days = None
    for arg in args:
        if arg.isdigit():
            days = int(arg)
            break

    cutoff = time.time() - days * 86400 if days is not None else None
    removed = 0
    freed = 0

    for name in os.listdir(books):
        if not name.endswith(".epub"):
            continue
        path = os.path.join(books, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if cutoff is not None and st.st_atime >= cutoff:
            continue
        try:
            os.remove(path)
            removed += 1
            freed += st.st_size
        except OSError as exc:
            print(f"could not remove {name}: {exc}")

    scope = f"older than {days} days" if days is not None else "all"
    print(f"removed {removed} EPUB(s) ({scope}), freed {epub.human_size(freed)}")


if __name__ == "__main__":
    main()
