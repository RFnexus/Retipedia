#!/bin/python3
import os
import template
import settings
import theme
import archives
from formatting import gutenberg

page = archives.page_root()

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)

print(template.render_header(zim))

if not zim:
    print("No archive selected.")
    print(f"`F{theme.LINK}`_`[Choose an archive`:{page}/index.mu]`_`f")
    raise SystemExit

meta = archives.load_meta(zim)
kind = archives.archive_type(zim)
print(f">{meta.get('title', zim)}")
if meta.get("description"):
    print(meta["description"])
count = meta.get("article_count")
if count:
    print(f"`Faaa{count:,} {'books' if kind == 'gutenberg' else 'entries'}`f")
print("")

if kind != "gutenberg":
    main = archives.main_path(zim)
    if main:
        print(f"`F{theme.LINK}`_`[Open main page`:{page}/entry.mu`zim={zim}|entry_path={main}]`_`f")
    print("Use the search field above to find entries in this archive.")
    raise SystemExit

view = os.environ.get("var_view", "")
letter = os.environ.get("var_letter", "")
author = os.environ.get("var_author", "")
shelf = os.environ.get("var_shelf", "")
per_page = 20
try:
    current_page = max(1, int(os.environ.get("var_page_number", 1)))
except ValueError:
    current_page = 1

archive = archives.open_archive(zim)
ext = gutenberg.suffix(archive)
base = f"{page}/zim_index.mu`zim={zim}"


def index_link(label, active=False, **fields):
    if active:
        return f"`!{label}`!"
    extra = "".join(f"|{key}={value}" for key, value in fields.items() if value)
    return f"`F{theme.NAV}`_`[{label}`:{base}{extra}]`_`f"


heading = ""
if author:
    view = "authors"
    rows = gutenberg.load_json(archive, f"auth_{author}_by_title.js")
    heading = gutenberg.author_name(archive, author) or "Unknown author"
elif shelf:
    view = "shelves"
    rows = gutenberg.shelf_books(archive, shelf)
    heading = gutenberg.shelf_names(archive).get(shelf, "")
    heading = f"{shelf} · {heading}" if heading else shelf
elif view == "popular":
    rows = gutenberg.load_json(archive, "full_by_popularity.js")
elif view == "authors":
    rows = gutenberg.load_json(archive, "authors.js")
elif view == "shelves":
    shelf_names = gutenberg.shelf_names(archive)
    rows = [[code, shelf_names.get(code, "")] for code in gutenberg.shelves(archive)]
else:
    view = "titles"
    rows = gutenberg.load_json(archive, "full_by_title.js")

context = {"view": view, "author": author, "shelf": shelf}
print(" · ".join([
    index_link("Titles", view == "titles"),
    index_link("Authors", view == "authors" and not author, view="authors"),
    index_link("Bookshelves", view == "shelves" and not shelf, view="shelves"),
    index_link("Popular", view == "popular", view="popular"),
]))
print("")
if heading:
    print(f">>{gutenberg.label(heading)}")

if view != "popular":
    rows = gutenberg.sorted_rows(rows)
    letters = sorted({b for b, _ in rows}, key=lambda b: (b == "#", b))
    if len(rows) > per_page:
        bar = [index_link("All", not letter, **context)]
        bar += [index_link(b, b == letter, letter=b, **context) for b in letters]
        print(" ".join(bar))
    if letter:
        rows = [row for b, row in rows if b == letter]
    else:
        rows = [row for _, row in rows]

noun = "books"
if view == "authors" and not author:
    noun = "authors"
elif view == "shelves" and not shelf:
    noun = "bookshelves"
total_pages = max(1, (len(rows) + per_page - 1) // per_page)
current_page = min(current_page, total_pages)
start = (current_page - 1) * per_page
print(f"`Faaa{len(rows):,} {noun} · page {current_page}/{total_pages}`f")
print("")

if not rows:
    print("Nothing listed here.")

for i, row in enumerate(rows[start:start + per_page], start=start + 1):
    if view == "authors" and not author:
        print(f"{i}. {index_link(gutenberg.label(row[0]), author=row[1])}")
    elif view == "shelves" and not shelf:
        line = f"{i}. {index_link(gutenberg.label(row[0]), shelf=row[0])}"
        if row[1]:
            line += f" `Faaa{gutenberg.label(row[1])}`f"
        print(line)
    else:
        title = gutenberg.label(row[0])
        path = gutenberg.book_entry(archive, row[0], row[3], ext)
        if path:
            line = f"{i}. `F{theme.LINK}`_`[{title}`:{page}/entry.mu`zim={zim}|{gutenberg.entry_fields(path)}]`_`f"
        else:
            line = f"{i}. {title}"
        if row[1]:
            line += f" `Faaa{gutenberg.label(row[1])}`f"
        print(line)

print("")
nav = []
if current_page > 1:
    nav.append(index_link("◀ Previous", letter=letter, page_number=current_page - 1, **context))
if current_page < total_pages:
    nav.append(index_link("Next ▶", letter=letter, page_number=current_page + 1, **context))
if nav:
    print("`c" + " · ".join(nav) + "`a")
