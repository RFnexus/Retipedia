#!/bin/python3
import os
import template
import settings
import theme
import archives

print(template.render_header())

rf = settings.root_folder
page = f"/page/{rf}" if rf else "/page"
items = archives.list_archives()

print(">Available Archives")
print("")

if not items:
    print("No archives configured.")
    print("Set `!zims_dir`! in settings.py and run `!generate_meta.py`! to add archives.")
else:
    for it in items:
        name = it["name"]
        title = it["title"]
        kind = it["type"]
        desc = it["description"]
        count = it["article_count"]
        if kind == "wikipedia":
            main = it["main_path"] or archives.main_path(name)
            link = f"{page}/entry.mu`zim={name}|entry_path={main}"
        elif kind in ("pdf", "video"):
            link = None
        else:
            link = f"{page}/zim_index.mu`zim={name}"
        if link:
            print(f"`F{theme.LINK}`_`[{title}`:{link}]`_`f")
        else:
            print(f"`!{title}`! (not browsable in a text browser)")
        info = []
        if kind:
            info.append(kind)
        if count:
            info.append(f"{count:,} articles")
        if info:
            print(f"`Faaa{' · '.join(info)}`f")
        if desc:
            print(desc)
        print("")
