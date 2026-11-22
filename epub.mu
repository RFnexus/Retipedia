#!/bin/python3
#
# epub.mu - on-demand EPUB download page for Retipedia.
#
# License: Unlicense (public domain) - see LICENSE.
#
# This software is possible because my parents believed in me and encouraged
# me to follow my passions.
#
# Linked as:  {page}/epub.mu`zim=<archive>|book=<id>
# Optionally with |entry_path=<path> and |variant=full|text
#
# NOTE: title is deliberately never passed as a link field. Some Gutenberg
# titles contain the same characters Micron uses for markup (backtick, pipe,
# ], =) - see gutenberg.UNSAFE_CHARS / gutenberg.entry_fields(). Title is
# always re-resolved server-side from entry_path/book instead.
#
import os

import settings
import theme
import archives
import template
import epub
from formatting import common

try:
    from formatting import gutenberg
except ImportError:  # pragma: no cover - only missing on a non-Retipedia host
    gutenberg = None

# This page has side effects (it extracts a file), so never cache it.
print("#!c=0")

page = archives.page_root()
names = archives.available_names()

zim = os.environ.get("var_zim") or (names[0] if names else None)
if zim not in names:
    zim = None

book = os.environ.get("var_book", "")
entry_path = os.environ.get("var_entry_path", "")
variant = os.environ.get("var_variant", "")
if variant not in ("full", "text"):
    variant = ""

print(template.render_header(zim))

if not zim:
    print("No archive selected.")
    print(f"`F{theme.LINK}`_`[Choose an archive`:{page}/index.mu]`_`f")
    raise SystemExit

if not epub.enabled():
    print(">EPUB downloads")
    print("EPUB downloads are turned off on this node.")
    raise SystemExit

if not book and not entry_path:
    print(">EPUB downloads")
    print("No book was specified.")
    raise SystemExit


def link_fields():
    """Fields for a link back to this book, escaped the same way Retipedia's
    own entry.mu links are (see gutenberg.entry_fields) - never embeds a raw
    path that might contain Micron's own markup characters."""
    if entry_path and gutenberg is not None:
        return gutenberg.entry_fields(entry_path)
    if book:
        return f"book={book}"
    if entry_path:
        return f"entry_path={entry_path}"
    return ""


def back_link():
    fields = f"zim={zim}|{link_fields()}"
    return f"`F{theme.LINK}`_`[← Back to the book`:{page}/entry.mu`{fields}]`_`f"


probe = epub.probe(zim, book, entry_path=entry_path)

if not probe.ok:
    print(">EPUB downloads")
    print(common.esc(probe.error or "Unknown error."))
    raise SystemExit

# Fill in whatever we were missing from the probe's own resolution, so
# link_fields()/back_link() and the extract() call below all use the same
# resolved values regardless of whether we started from a book id or a path.
if probe.entry_path:
    entry_path = probe.entry_path
if not book and entry_path and gutenberg is not None:
    book = gutenberg.book_id(entry_path)
title = probe.title

display_title = title or (f"Book {book}" if book else "this book")
print(f">{common.esc(display_title)}")

# Only show a full-vs-text choice when there's a genuine decision to make:
# a real EPUB exists in the archive AND building a lighter one is allowed.
# Otherwise this behaves exactly as a single-outcome page, same as before
# variants existed.
offer_choice = probe.has_full and epub.fallback_enabled()

if offer_choice and not variant:
    full_size = epub.human_size(probe.full_size)
    choice_fields = f"zim={zim}|{link_fields()}"
    print("This book has two versions available.")
    print("")
    print(f"`F{theme.LINK}`_`[⤓ Full EPUB · {full_size}`:{page}/epub.mu`{choice_fields}|variant=full]`_`f")
    print("`Faaaincludes original formatting and illustrations`f")
    print("")
    print(f"`F{theme.LINK}`_`[⤓ Text-only EPUB`:{page}/epub.mu`{choice_fields}|variant=text]`_`f")
    print("`Faaano illustrations - much smaller, for slow links or size-limited clients`f")
    print("")
    print("-─")
    print(back_link())
    raise SystemExit

# No real choice to offer: fall back to "auto" (prefer the real EPUB, build
# a text-only one if the archive has none) unless the caller already picked
# a variant explicitly from the choice screen above.
effective_variant = variant or "auto"
result = epub.extract(zim, book, title=title, entry_path=entry_path, variant=effective_variant)

if not result.ok:
    print(f"`F{theme.NAV}Could not prepare this EPUB.`f")
    print("")
    print(common.esc(result.error or "Unknown error."))
    print("")
    print(back_link())
    raise SystemExit

size_str = epub.human_size(result.size)
url = result.url

print("")

if result.existed:
    # Already extracted on an earlier request, so the node has registered it.
    print(f"`F{theme.LINK}`_`[⤓ Download EPUB · {size_str}`:{url}]`_`f")
    print("")
    print(f"`Faaafile: {common.esc(result.filename)}`f")
else:
    wait = result.ready_in
    print(f"Extracted from the archive · {size_str}")
    print("")
    if wait > 0:
        mins = max(1, wait // 60)
        unit = "minute" if mins == 1 else "minutes"
        print(f"`F{theme.NAV}The node picks up new files every {mins} {unit}.`f")
        print("Reload this page in a moment, then the download link below will work.")
        print("")
    else:
        print(f"`F{theme.NAV}Ready in about a second.`f")
        print("")
    print(f"`F{theme.LINK}`_`[⤓ Download EPUB · {size_str}`:{url}]`_`f")
    if wait > 0:
        print("")
        reload_fields = f"zim={zim}|{link_fields()}"
        if variant:
            reload_fields += f"|variant={variant}"
        print(f"`F{theme.NAV}`_`[⟳ Reload this page`:{page}/epub.mu`{reload_fields}]`_`f")

if result.source == "converted" and variant != "text":
    print("")
    print("`FaaaThis archive had no EPUB for this book, so one was built from the text.`f")
elif variant == "text":
    print("")
    print("`FaaaText-only version - no illustrations.`f")

print("")
print("-─")
print(back_link())
