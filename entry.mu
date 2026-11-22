#!/bin/python3
import os
import settings
import theme
import archives
import cache
import media
from formatting import common, wikipedia, generic, gutenberg, stackexchange, ifixit, medlineplus

page = archives.page_root()

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)
if zim not in names:
    zim = None
entry_path = os.environ.get("var_entry_path", "")
book = os.environ.get("var_book", "")
chunk = os.environ.get("var_chunk")
fmt = os.environ.get("var_format")
layout = os.environ.get("var_layout") or getattr(settings, "text_layout", "wide")
text_width = getattr(settings, "text_width", 72)

kind = archives.archive_type(zim) if zim else "generic"

if chunk is None and kind == "gutenberg":
    chunk = "parts"
page_no = None
if chunk == "full":
    chunk = None
elif chunk and chunk[:1] == "p" and chunk[1:].isdigit():
    # pN = page N of the paged "full" view (see full_pages below)
    page_no = max(1, int(chunk[1:]))
    chunk = None


def dump_raw(text):
    for line in text.split("\n"):
        print(common.guard(common.esc(line)))


def resolve_entry():
    archive = archives.open_archive(zim)
    path = entry_path
    if kind == "gutenberg":
        if book and not path:
            path = gutenberg.path_for_id(archive, book)
        mapped = gutenberg.book_path(path)
        if mapped != path and archive.has_entry_by_path(mapped):
            path = mapped
    entry = archive.get_entry_by_path(path)
    if entry.is_redirect:
        entry = entry.get_redirect_entry()
    title = entry.title
    if kind == "gutenberg" and title == entry.path:
        title = gutenberg.book_title(title)
    return archive, title, entry.get_item()


def render_micron(item, path):
    validator = f"{item.size}-{common.RENDER_VERSION}-{kind}-{text_width}-{getattr(settings, 'images', False)}"
    micron = cache.get(zim, path, validator)
    if micron is not None and media.missing(micron):
        micron = None
    if micron is None:
        html = bytes(item.content).decode("utf-8", "replace")
        if kind == "wikipedia":
            micron = wikipedia.html_to_micron(html, zim=zim, entry_path=path)
        elif kind == "gutenberg":
            micron = gutenberg.html_to_micron(html, zim=zim, entry_path=path)
        elif kind == "stackexchange":
            micron = stackexchange.html_to_micron(html, zim=zim, entry_path=path)
        elif kind == "ifixit":
            micron = ifixit.html_to_micron(html, zim=zim, entry_path=path)
        elif kind == "medlineplus":
            micron = medlineplus.html_to_micron(html, zim=zim, entry_path=path)
        else:
            micron = generic.html_to_micron(html, zim=zim, entry_path=path)
        cache.put(zim, path, validator, micron)
    return micron


if fmt in ("micron", "html") and zim and (entry_path or book):
    try:
        archive, title, item = resolve_entry()
        path = item.path
        if not item.mimetype.startswith("text/html"):
            print("This entry is not a readable text document.")
        elif fmt == "html":
            dump_raw(bytes(item.content).decode("utf-8", "replace"))
        else:
            dump_raw(render_micron(item, path))
    except KeyError:
        print("Can't find entry")
    except FileNotFoundError:
        print("Archive not found")
    raise SystemExit

resolved = None
error = ""
if zim and (entry_path or book):
    try:
        resolved = resolve_entry()
    except KeyError:
        error = "Can't find entry"
    except FileNotFoundError:
        error = "Archive not found"

print(f"#!c={getattr(settings, 'page_cache', 604800) if resolved else 0}")

import template

print(template.render_header(zim))

if not zim:
    print("No archive selected.")
    print(f"`F{theme.LINK}`_`[Choose an archive`:{page}/index.mu]`_`f")
    raise SystemExit

if not entry_path and not book:
    print(f">{archives.load_meta(zim).get('title', zim)}")
    print("Use the search field above to find an entry.")
    raise SystemExit

if error:
    print(error)
    raise SystemExit


def nav_line(idx, total, base):
    parts = []
    if idx > 1:
        parts.append(f"`F{theme.NAV}`_`[◀ Prev`:{page}/entry.mu`{base}|chunk={idx - 1}]`_`f")
    parts.append(f"`F{theme.NAV}`_`[Parts`:{page}/entry.mu`{base}|chunk=parts]`_`f")
    parts.append(f"`F{theme.NAV}`_`[Full`:{page}/entry.mu`{base}|chunk=full]`_`f")
    if idx < total:
        parts.append(f"`F{theme.NAV}`_`[Next ▶`:{page}/entry.mu`{base}|chunk={idx + 1}]`_`f")
    return "`c" + " · ".join(parts) + "`a"


def full_pages(micron, chunks):
    """Split a large entry's "full" view into pages of whole parts.

    Very large entries (whole books) are slow to download over a mesh and
    too heavy for some clients to render in one page (MeshChatX freezes on
    100k+ lines). Pages are built from the existing parts, so they break at
    the same safe points (never inside a table, preferably at sections).
    Returns None when the entry fits in one page.
    """
    cap = getattr(settings, "full_page_max", 120000)
    if not cap or common.byte_size(micron) <= cap:
        return None
    pages, cur, size = [], [], 0
    for i, piece in enumerate(chunks, start=1):
        b = common.byte_size(piece) + 1
        if cur and size + b > cap:
            pages.append(cur)
            cur, size = [], 0
        cur.append(i)
        size += b
    if cur:
        pages.append(cur)
    return pages if len(pages) > 1 else None


def page_nav(n, count, base):
    parts = []
    if n > 1:
        parts.append(f"`F{theme.NAV}`_`[◀ Prev page`:{page}/entry.mu`{base}|chunk=p{n - 1}]`_`f")
    parts.append(f"`F{theme.NAV}`_`[Parts`:{page}/entry.mu`{base}|chunk=parts]`_`f")
    if n < count:
        parts.append(f"`F{theme.NAV}`_`[Next page ▶`:{page}/entry.mu`{base}|chunk=p{n + 1}]`_`f")
    return "`c" + " · ".join(parts) + "`a"


def layout_line(plain, current):
    parts = []
    for name, label in (("wide", "Wide"), ("narrow", "Narrow"), ("center", "Centered")):
        if name == layout:
            parts.append(f"`!{label}`!")
        else:
            fields = f"{plain}|layout={name}|chunk={current}"
            parts.append(f"`F{theme.NAV}`_`[{label}`:{page}/entry.mu`{fields}]`_`f")
    return "`Faaalayout:`f " + " · ".join(parts)


try:
    archive, title, item = resolved
    entry_path = item.path
    base = f"zim={zim}|entry_path={entry_path}"
    if kind == "gutenberg":
        base = f"zim={zim}|{gutenberg.entry_fields(entry_path)}"
    plain = base
    base += f"|layout={layout}"

    if kind in ("pdf", "video"):
        print(f">{title}")
        print(f"This entry is a {kind} document and cannot be displayed in a text browser.")
        raise SystemExit
    if not item.mimetype.startswith("text/html"):
        print(f">{title}")
        print("This entry is not a readable text document.")
        raise SystemExit
    listing = gutenberg.listing_fields(archive, entry_path) if kind == "gutenberg" else ""
    if listing:
        print(f">{title}")
        print("This page is a book listing that is built by scripts in a web browser.")
        print(f"`F{theme.LINK}`_`[Browse it in the directory index`:{page}/zim_index.mu`zim={zim}|{listing}]`_`f")
        raise SystemExit

    micron = render_micron(item, entry_path)
    if layout in ("narrow", "center"):
        micron = common.reflow(micron, text_width, layout == "center")
    size_str = common.human_size(common.byte_size(micron))
    chunks = common.chunk_micron(micron, getattr(settings, "chunk_size", 4096))
    total = len(chunks)
    plural = "part" if total == 1 else "parts"
    if chunk == "parts" and total == 1:
        chunk = None
    pages = full_pages(micron, chunks)

    print(f">{title}")

    if chunk is None:
        actions = [f"`Faaa{size_str}`f"]
        if total > 1:
            actions.append(f"`F{theme.NAV}`_`[⇊ {total} parts`:{page}/entry.mu`{base}|chunk=parts]`_`f")
        actions.append(f"`F{theme.NAV}`_`[⤓ Micron {size_str}`:{page}/entry.mu`{base}|format=micron]`_`f")
        actions.append(f"`F{theme.NAV}`_`[⤓ HTML {common.human_size(item.size)}`:{page}/entry.mu`{base}|format=html]`_`f")
        print("`c" + " · ".join(actions) + "`a")
        if pages:
            n = min(page_no or 1, len(pages))
            group = pages[n - 1]
            nav = page_nav(n, len(pages), base)
            print(f"`c`Faaapage {n}/{len(pages)} · parts {group[0]}-{group[-1]} of {total}`f`a")
            print(nav)
            print(layout_line(plain, f"p{n}"))
            print("-─")
            print("\n".join(chunks[i - 1] for i in group))
            print("`a")
            print("-─")
            print(nav)
        else:
            print(layout_line(plain, "full"))
            print("-─")
            print(micron)
            print("`a")

    elif chunk == "parts":
        sections = {}
        for level, sec_title, ci in common.section_index(chunks):
            sections.setdefault(ci, []).append(sec_title)
        print(f"`Faaa{size_str} of readable text · {total} {plural}`f")
        full_label = f"Read full entry ({len(pages)} pages)" if pages else "Read full entry"
        print(f"`F{theme.NAV}`_`[{full_label}`:{page}/entry.mu`{base}|chunk=full]`_`f")
        print(layout_line(plain, "parts"))
        print("")
        print("Select a part to read:")
        print("")
        for i, piece in enumerate(chunks, start=1):
            here = sections.get(i) or (["Introduction"] if i == 1 else [])
            desc = ", ".join(here[:3])
            label = f"Part {i} — {common.human_size(common.byte_size(piece))}"
            line = f"• `F{theme.NAV}`_`[{label}`:{page}/entry.mu`{base}|chunk={i}]`_`f"
            if desc:
                line += f"  `Faaa{desc}`f"
            print(line)

    else:
        try:
            idx = max(1, min(int(chunk), total))
        except ValueError:
            idx = 1
        nav = nav_line(idx, total, base)
        print(f"`c`Faaapart {idx}/{total} · {size_str} total`f`a")
        print(nav)
        print(layout_line(plain, idx))
        print("-─")
        print(chunks[idx - 1])
        print("`a")
        print("-─")
        print(nav)

except KeyError:
    print("Can't find entry")
except FileNotFoundError:
    print("Archive not found")
