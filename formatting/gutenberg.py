import re
import settings
from bs4 import BeautifulSoup, NavigableString, Tag
from formatting.common import (
    norm_space, esc, guard, render_inline, render_list, render_dl,
    render_blockquote, render_table, emit_blank, emit_text_block, collapse, new_ctx,
)

REMOVE_TAGS = ["script", "style", "link", "img", "header", "footer", "nav",
               "form", "input", "svg", "button", "noscript"]
REMOVE_IDS = ["pg-header", "pg-machine-header", "pg-footer",
              "pg-start-separator", "pg-end-separator", "spinner"]
REMOVE_CLASSES = ["l10nselector", "spinner", "pg-boilerplate", "navbar"]

_COVER_RE = re.compile(r"_cover\.(\d+)$")


def book_path(path):
    return _COVER_RE.sub(r".\1", path or "")


def clean_html(root):
    for tag in root.find_all(REMOVE_TAGS):
        tag.decompose()
    for el_id in REMOVE_IDS:
        el = root.find(id=el_id)
        if el:
            el.decompose()
    for cls in REMOVE_CLASSES:
        for el in root.find_all(class_=cls):
            el.decompose()


def render_pre(node, lines):
    text = node.get_text().replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text.strip():
        return
    emit_blank(lines)
    for ln in text.split("\n"):
        lines.append(guard(esc(ln.rstrip())))
    lines.append("")


def render_blocks(node, ctx, lines, depth=0):
    for child in node.children:
        if isinstance(child, NavigableString):
            text = norm_space(esc(str(child))).strip()
            if text:
                emit_text_block(lines, text)
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in ("script", "style", "link"):
            continue
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            title = norm_space(child.get_text(" ", strip=True)).strip()
            if title:
                emit_blank(lines)
                lines.append(">" * min(int(name[1]), 4) + esc(title))
                lines.append("")
        elif name == "p":
            emit_text_block(lines, render_inline(child, ctx))
        elif name in ("ul", "ol"):
            render_list(child, ctx, lines, name == "ol", depth)
        elif name == "dl":
            render_dl(child, ctx, lines, depth)
        elif name == "blockquote":
            render_blockquote(child, ctx, lines)
        elif name == "pre":
            render_pre(child, lines)
        elif name == "table":
            render_table(child, ctx, lines)
        else:
            render_blocks(child, ctx, lines, depth)


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    root = (soup.find(class_="document") or soup.find(id="content")
            or soup.body or soup)
    clean_html(root)
    ctx = new_ctx(settings.root_folder, zim=zim, entry_path=entry_path)
    lines = []
    render_blocks(root, ctx, lines)
    return "`:top\n" + collapse("\n".join(lines)) + "\n"
