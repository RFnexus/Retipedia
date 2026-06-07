#!/bin/python3
import os
import settings
import theme
import archives
import cache
from formatting import common, wikipedia, generic, gutenberg

rf = settings.root_folder

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)
entry_path = os.environ.get("var_entry_path", "")
chunk = os.environ.get("var_chunk")
fmt = os.environ.get("var_format")

kind = archives.archive_type(zim) if zim else "generic"

if kind == "gutenberg" and entry_path:
    entry_path = gutenberg.book_path(entry_path)


def dump_raw(text):
    for line in text.split("\n"):
        print(common.guard(common.esc(line)))


def resolve_entry():
    archive = archives.open_archive(zim)
    entry = archive.get_entry_by_path(entry_path)
    if entry.is_redirect:
        entry = entry.get_redirect_entry()
    return entry.title, entry.get_item()


def render_micron(item, path):
    validator = f"{item.size}-{common.RENDER_VERSION}"
    micron = cache.get(zim, path, validator)
    if micron is None:
        html = bytes(item.content).decode("utf-8", "replace")
        if kind == "wikipedia":
            micron = wikipedia.html_to_micron(html, zim=zim, entry_path=path)
        elif kind == "gutenberg":
            micron = gutenberg.html_to_micron(html, zim=zim, entry_path=path)
        else:
            micron = generic.html_to_micron(html, zim=zim, entry_path=path)
        cache.put(zim, path, validator, micron)
    return micron


if fmt in ("micron", "html") and zim and entry_path:
    try:
        title, item = resolve_entry()
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

import template

print(template.render_header(zim))

if not zim:
    print("No archive selected.")
    print(f"`F{theme.LINK}`_`[Choose an archive`:/page/{rf}/index.mu]`_`f")
    raise SystemExit

if not entry_path:
    print(f">{archives.load_meta(zim).get('title', zim)}")
    print("Use the search field above to find an entry.")
    raise SystemExit


def nav_line(idx, total, base):
    parts = []
    if idx > 1:
        parts.append(f"`F{theme.NAV}`_`[◀ Prev`:/page/{rf}/entry.mu`{base}|chunk={idx - 1}]`_`f")
    parts.append(f"`F{theme.NAV}`_`[Parts`:/page/{rf}/entry.mu`{base}|chunk=parts]`_`f")
    parts.append(f"`F{theme.NAV}`_`[Full`:/page/{rf}/entry.mu`{base}]`_`f")
    if idx < total:
        parts.append(f"`F{theme.NAV}`_`[Next ▶`:/page/{rf}/entry.mu`{base}|chunk={idx + 1}]`_`f")
    return "`c" + " · ".join(parts) + "`a"


try:
    title, item = resolve_entry()
    entry_path = item.path
    base = f"zim={zim}|entry_path={entry_path}"

    if kind in ("pdf", "video"):
        print(f">{title}")
        print(f"This entry is a {kind} document and cannot be displayed in a text browser.")
        raise SystemExit
    if not item.mimetype.startswith("text/html"):
        print(f">{title}")
        print("This entry is not a readable text document.")
        raise SystemExit

    micron = render_micron(item, entry_path)
    size_str = common.human_size(common.byte_size(micron))
    chunks = common.chunk_micron(micron, getattr(settings, "chunk_size", 4096))
    total = len(chunks)
    plural = "part" if total == 1 else "parts"

    print(f">{title}")

    if chunk is None:
        actions = [f"`Faaa{size_str}`f"]
        if total > 1:
            actions.append(f"`F{theme.NAV}`_`[⇊ {total} parts`:/page/{rf}/entry.mu`{base}|chunk=parts]`_`f")
        actions.append(f"`F{theme.NAV}`_`[⤓ Micron {size_str}`:/page/{rf}/entry.mu`{base}|format=micron]`_`f")
        actions.append(f"`F{theme.NAV}`_`[⤓ HTML {common.human_size(item.size)}`:/page/{rf}/entry.mu`{base}|format=html]`_`f")
        print("`c" + " · ".join(actions) + "`a")
        print("-─")
        print(micron)

    elif chunk == "parts":
        sections = {}
        for level, sec_title, ci in common.section_index(chunks):
            sections.setdefault(ci, []).append(sec_title)
        print(f"`Faaa{size_str} of readable text · {total} {plural}`f")
        print(f"`F{theme.NAV}`_`[Read full entry`:/page/{rf}/entry.mu`{base}]`_`f")
        print("")
        print("Select a part to read:")
        print("")
        for i, piece in enumerate(chunks, start=1):
            here = sections.get(i) or (["Introduction"] if i == 1 else [])
            desc = ", ".join(here[:3])
            label = f"Part {i} — {common.human_size(common.byte_size(piece))}"
            line = f"• `F{theme.NAV}`_`[{label}`:/page/{rf}/entry.mu`{base}|chunk={i}]`_`f"
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
        print("-─")
        print(chunks[idx - 1])
        print("-─")
        print(nav)

except KeyError:
    print("Can't find entry")
except FileNotFoundError:
    print("Archive not found")
