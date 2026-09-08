#!/bin/python3
import os
import settings
import theme
import archives

ascii_art = r"""`c`F09f
  ____           _     _                      _   _         
 |  _ \\    ___  | |_  (_)  _ __     ___    __| | (_)   __ _ 
 | |_) |  / _ \\ | __| | | | '_ \\   / _ \\  / _` | | | |  / _`   |
 |  _ <  |  __/ | |_  | | | |_) | |  __/ | (_| | | | | (_| |
 |_| \\_\\  \\___|  \\__| |_| | .__/   \\___|  \\__,_| |_|  \\__,_|
                          |_|                               

`f``""".replace("`F09f", "`F" + theme.HEADER)


search_icon = "🔍"


def render_header(zim=None):
    page = archives.page_root()
    nav = f"`F{theme.HEADER}`_`[Archives`:{page}/index.mu]`_`f | `F{theme.HEADER}`_`[Info`:{page}/info.mu]`_`f"
    head = f"""
`c
`Faaa{settings.node_title}`f |  {nav} \

`a
--  `b
"""
    if zim:
        head += f"""
`B111 {search_icon} `b  `B555`<search_query` >`b   \
`F{theme.BRIGHT}`!`[Search`:{page}/results.mu`search_query|zim={zim}]`!`b `f
"""
    head += "\n-¯\n"
    return head


header = render_header()

if settings.ascii_art_enabled:
    print(ascii_art)
