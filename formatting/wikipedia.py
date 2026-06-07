import settings
from bs4 import BeautifulSoup, NavigableString, Tag
from formatting import common
from formatting.common import (
    norm_space, esc, slug, clean_label, render_inline, render_list, render_dl,
    render_blockquote, render_table, emit_blank, emit_text_block, collapse,
    new_ctx, NAV_COLOR,
)

REMOVE_CLASSES = [
    "navbox", "navbox-styles", "navbox-inner", "vertical-navbox", "nomobile",
    "sidebar", "infobox", "hatnote", "navigation-not-searchable", "metadata",
    "mw-editsection", "noprint", "mw-jump-link", "gallery", "thumb", "thumbinner",
    "mw-empty-elt", "ambox", "mbox-small", "authority-control", "toc",
    "shortdescription", "printfooter", "catlinks", "noviewer",
]

TOC_PLACEHOLDER = "\x00RETIPEDIA_TOC\x00"


def clean_html(root):
    for tag in root.find_all(["script", "style", "link", "img", "figure",
                              "audio", "video", "map", "meta"]):
        tag.decompose()
    for cls in REMOVE_CLASSES:
        for el in root.find_all(class_=cls):
            el.decompose()
    for el in root.find_all("sup", class_="noprint"):
        el.decompose()


def _emit_heading(h, ctx, lines):
    level = int(h.name[1])
    title = norm_space(h.get_text(" ", strip=True)).strip()
    if not title:
        return
    if not ctx["toc_inserted"]:
        lines.append(TOC_PLACEHOLDER)
        ctx["toc_inserted"] = True
    if level in (2, 3):
        ctx["toc"].append((level, title, slug(title)))
    marks = ">" * min(level, 4)
    emit_blank(lines)
    lines.append(f"{marks}{esc(title)}")
    lines.append("")


def render_references(node, ctx, lines):
    emit_blank(lines)
    for li in node.find_all("li", recursive=False):
        anchor = slug(li.get("id", ""))
        num = ctx["cite_numbers"].get(anchor)
        if num is None:
            ctx["ref_counter"] += 1
            num = str(ctx["ref_counter"])
        backlink = ""
        back_span = li.find("span", class_="mw-cite-backlink")
        if back_span:
            back = back_span.find("a", href=True)
            if back and back["href"].startswith("#cite_ref"):
                dest = slug(back["href"][1:])
                if dest in ctx["emitted"]:
                    backlink = f" `F{NAV_COLOR}`_`[↑`#{dest}]`_`f"
            back_span.decompose()
        text_node = li.find("span", class_="reference-text")
        if text_node:
            text = render_inline(text_node, ctx)
        else:
            text = esc(norm_space(li.get_text(" ", strip=True)))
        text = norm_space(text).strip()
        lines.append(f"`:{anchor}`!{num}.`!{backlink} {text}")
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
        classes = child.get("class") or []
        if name in ("script", "style", "link", "sup", "sub"):
            continue
        if name == "div" and "mw-heading" in classes:
            heading = child.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if heading:
                _emit_heading(heading, ctx, lines)
        elif name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            _emit_heading(child, ctx, lines)
        elif name == "p":
            emit_text_block(lines, render_inline(child, ctx))
        elif name in ("ul", "ol"):
            if name == "ol" and "references" in classes:
                render_references(child, ctx, lines)
            else:
                render_list(child, ctx, lines, name == "ol", depth)
        elif name == "dl":
            render_dl(child, ctx, lines, depth)
        elif name == "blockquote":
            render_blockquote(child, ctx, lines)
        elif name == "pre":
            common.render_code(child, lines)
        elif name == "table":
            if "wikitable" in classes:
                render_table(child, ctx, lines)
        else:
            render_blocks(child, ctx, lines, depth)


def _build_toc(ctx):
    items = ctx["toc"]
    if len(items) < 2:
        return ""
    lines = [">>Contents", ""]
    for level, title, anchor in items:
        indent = "  " if level == 3 else ""
        lines.append(f"{indent}• `F{NAV_COLOR}`_`[{clean_label(title)}`#{anchor}]`_`f")
    lines.append("")
    lines.append("-─")
    lines.append("")
    return "\n".join(lines)


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    root = soup.find(class_="mw-parser-output") or soup.body or soup
    clean_html(root)

    ctx = new_ctx(settings.root_folder, zim=zim, entry_path=entry_path)

    body_lines = []
    render_blocks(root, ctx, body_lines)
    body = collapse("\n".join(body_lines))
    body = body.replace(TOC_PLACEHOLDER, _build_toc(ctx))

    document = "`:top\n" + body
    if ctx["toc_inserted"]:
        document += f"\n\n`c`F{NAV_COLOR}`_`[↑ Back to top`#top]`_`f`a\n"
    return collapse(document) + "\n"
