#!/bin/python3
import os
import template
import settings
import theme
import archives

rf = settings.root_folder

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)

print(template.render_header(zim))

if not zim:
    print("No archive selected.")
    print(f"`F{theme.LINK}`_`[Choose an archive`:/page/{rf}/index.mu]`_`f")
    raise SystemExit

meta = archives.load_meta(zim)
print(f">{meta.get('title', zim)}")
if meta.get("description"):
    print(meta["description"])
count = meta.get("article_count")
if count:
    print(f"`Faaa{count:,} entries`f")
print("")

main = archives.main_path(zim)
if main:
    print(f"`F{theme.LINK}`_`[Open main page`:/page/{rf}/entry.mu`zim={zim}|entry_path={main}]`_`f")
print("Use the search field above to find entries in this archive.")
