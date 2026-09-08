import re
import json
import unicodedata
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from formatting.common import (
    norm_space, esc, guard, slug, render_inline, render_inline_node, render_list,
    render_dl, render_table, emit_blank, collapse, new_ctx,
)

REMOVE_TAGS = ["script", "style", "link", "img", "figure", "header", "footer", "nav",
               "form", "input", "svg", "button", "noscript"]
REMOVE_IDS = ["pg-header", "pg-machine-header", "pg-footer",
              "pg-start-separator", "pg-end-separator", "spinner"]
REMOVE_CLASSES = ["l10nselector", "spinner", "pg-boilerplate", "navbar", "figcenter",
                  "figleft", "figright", "caption", "pagenum", "pageno"]
POEM_CLASSES = {"poem", "stanza", "verse", "poetry"}
QUOTE_CLASSES = {"blockquote", "blockquot", "blkquot", "quote"}
ALIGN_CLASSES = {"center": "`c", "centered": "`c", "right": "`r"}
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")

_COVER_RE = re.compile(r"_cover\.(\d+)(\.html)?$")
_ID_RE = re.compile(r"^(.*?)(_cover)?\.(\d+)(\.html)?$")
_LEAD_RE = re.compile(r"^[\W_]+")
_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")
_BODY_RE = re.compile(r"<body[^>]*class=\"([^\"]*)\"")
_INDENT_RE = re.compile(r"\bi(\d+)\b")
_LEAD_WS_RE = re.compile(r"\s*")
_L10N_RE = re.compile(r"<script type=\"application/l10n\">(.*?)</script>", re.S)
LISTING_CLASSES = {"home", "lcc_shelf_home", "bookshelf_home", "individual_book_shelf"}
UNSAFE_CHARS = "`|]="


def book_path(path):
    return _COVER_RE.sub(r".\1\2", path or "")


def book_title(title):
    title = _ID_RE.sub(r"\1", title or "")
    return title[:-5] if title.endswith(".html") else title


def book_id(path):
    m = _ID_RE.match(path or "")
    return m.group(3) if m else ""


def entry_fields(path):
    if any(c in path for c in UNSAFE_CHARS) and book_id(path):
        return f"book={book_id(path)}"
    return f"entry_path={path}"


def label(text):
    text = norm_space(text).strip().replace("`", "'")
    return text.replace("[", "(").replace("]", ")")


def load_json(archive, path):
    try:
        item = archive.get_entry_by_path(path).get_item()
    except KeyError:
        return []
    text = bytes(item.content).decode("utf-8", "replace")
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return []


def suffix(archive):
    return ".html" if archive.has_entry_by_path("Home.html") else ""


def fs_name(title):
    return (title or "").strip().replace("/", "-")[:230]


def book_entry(archive, title, book_id, ext):
    stem = fs_name(title)
    for candidate in (f"{stem}.{book_id}{ext}", f"{stem}_cover.{book_id}{ext}"):
        if archive.has_entry_by_path(candidate):
            return candidate
    return ""


def path_for_id(archive, book_id):
    for row in load_json(archive, "full_by_title.js"):
        if str(row[3]) == str(book_id):
            return book_entry(archive, row[0], row[3], suffix(archive))
    return ""


def author_name(archive, author_id):
    for name, aid in load_json(archive, "authors.js"):
        if str(aid) == str(author_id):
            return name
    return ""


def shelves(archive):
    return load_json(archive, "lcc_shelves.js") or load_json(archive, "bookshelves.js")


def shelf_books(archive, shelf):
    return (load_json(archive, f"lcc_shelf_{shelf}_by_title.js")
            or load_json(archive, f"bookshelf_{shelf}_by_title.js"))


def shelf_names(archive):
    names = {}
    for home in ("Home", "Home.html"):
        if not archive.has_entry_by_path(home):
            continue
        html = bytes(archive.get_entry_by_path(home).get_item().content).decode("utf-8", "replace")
        m = _L10N_RE.search(html)
        try:
            strings = json.loads(m.group(1))["locales"]["en"]
        except (AttributeError, ValueError, KeyError, TypeError):
            return names
        for key, value in strings.items():
            if key.startswith("lcc-shelf-"):
                text = value.get("textContent", "")
                names[key[10:]] = text.split("-", 1)[1] if "-" in text else text
    return names


def sort_key(text):
    key = "".join(c for c in unicodedata.normalize("NFKD", text or "")
                  if not unicodedata.combining(c)).lower()
    key = _LEAD_RE.sub("", key)
    return _ARTICLE_RE.sub("", key) or key


def bucket(key):
    return key[:1].upper() if key[:1].isalpha() else "#"


def sorted_rows(rows):
    keyed = sorted(((sort_key(row[0]), row) for row in rows), key=lambda kr: kr[0])
    return [(bucket(key), row) for key, row in keyed]


def is_listing(html):
    m = _BODY_RE.search(html or "")
    classes = set((m.group(1) if m else "").split())
    return 'id="books_table"' in html or bool(classes & LISTING_CLASSES)


def listing_fields(archive, path):
    stem = path[:-5] if path.endswith(".html") else path
    if stem == "Home":
        return "view=titles"
    if stem in ("lcc_shelf_home", "bookshelf_home"):
        return "view=shelves"
    if stem.startswith("lcc_shelf_"):
        return f"shelf={stem[10:]}"
    if archive.has_entry_by_path(f"bookshelf_{stem}_by_title.js"):
        return f"shelf={stem}"
    m = _ID_RE.match(stem)
    if m and not m.group(2) and archive.has_entry_by_path(f"auth_{m.group(3)}_by_title.js"):
        try:
            html = bytes(archive.get_entry_by_path(path).get_item().content).decode("utf-8", "replace")
        except KeyError:
            return ""
        if is_listing(html):
            return f"author={m.group(3)}"
    return ""


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


def emit_para(lines, text, indent=""):
    text = text.strip("\n")
    if not text.strip():
        return
    emit_blank(lines)
    for sub in text.split("\n"):
        sub = sub.strip()
        if sub:
            lines.append(indent + guard(sub))
    lines.append("")


def heading_anchor(node):
    ids = [node.get("id")] + [a.get("id") or a.get("name") for a in node.find_all("a")]
    if isinstance(node.parent, Tag) and node.parent.name == "div":
        ids.append(node.parent.get("id"))
    for value in ids:
        if value:
            return slug(value)
    return ""


def render_heading(node, lines):
    title = norm_space(node.get_text(" ", strip=True)).strip()
    if not title:
        return
    emit_blank(lines)
    anchor = heading_anchor(node)
    if anchor:
        lines.append(f"`:{anchor}")
    lines.append(">" * min(int(node.name[1]), 4) + esc(title))
    lines.append("")


def poem_lines(node, ctx):
    spans_are_lines = (not node.find("br", recursive=False)
                       and len(node.find_all("span", recursive=False)) > 1)
    rows = [["", ""]]
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            raw = str(child)
            lead = _LEAD_WS_RE.match(raw).group(0)
            if "\n" in lead and not rows[-1][1].strip() and not rows[-1][0]:
                rows[-1][0] = " " * len(lead.rsplit("\n", 1)[-1].replace("\xa0", " ").expandtabs(4))
            rows[-1][1] += esc(norm_space(raw))
        elif not isinstance(child, Tag):
            continue
        elif child.name == "br":
            rows.append(["", ""])
        elif child.name == "span":
            m = _INDENT_RE.search(" ".join(child.get("class") or []))
            if spans_are_lines and rows[-1][1].strip():
                rows.append(["", ""])
            if m:
                rows[-1][0] = " " * int(m.group(1))
            rows[-1][1] += render_inline(child, ctx)
        else:
            rows[-1][1] += render_inline_node(child, ctx)
    return rows


def render_poem(node, ctx, lines):
    blocks = [c for c in node.children if isinstance(c, Tag) and c.name in ("div", "p")]
    if blocks:
        for block in blocks:
            render_poem(block, ctx, lines)
        return
    out = []
    for indent, text in poem_lines(node, ctx):
        pieces = [p.strip() for p in text.split("\n")]
        pieces = [p for p in pieces if p]
        if pieces:
            out.extend(indent + guard(p) for p in pieces)
        elif out and out[-1] != "":
            out.append("")
    while out and out[-1] == "":
        out.pop()
    if out:
        emit_blank(lines)
        lines.extend(out)
        lines.append("")


def render_blocks(node, ctx, lines, depth=0, indent=""):
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            text = norm_space(esc(str(child))).strip()
            if text:
                emit_para(lines, text, indent)
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        classes = set(child.get("class") or [])
        if name in ("script", "style", "link"):
            continue
        if name in HEADINGS:
            render_heading(child, lines)
        elif classes & POEM_CLASSES:
            render_poem(child, ctx, lines)
        elif name == "blockquote" or classes & QUOTE_CLASSES:
            if name == "p":
                emit_para(lines, render_inline(child, ctx), indent + "  ")
            else:
                render_blocks(child, ctx, lines, depth, indent + "  ")
        elif name == "p":
            align = next((ALIGN_CLASSES[c] for c in classes if c in ALIGN_CLASSES), "")
            text = render_inline(child, ctx)
            if align:
                text = "\n".join(f"{align}{ln.strip()}`a" for ln in text.split("\n") if ln.strip())
            emit_para(lines, text, indent)
        elif name in ("ul", "ol"):
            render_list(child, ctx, lines, name == "ol", depth)
        elif name == "dl":
            render_dl(child, ctx, lines, depth)
        elif name == "pre":
            render_pre(child, lines)
        elif name == "table":
            render_table(child, ctx, lines)
        elif name == "hr":
            emit_blank(lines)
            lines.append("-─")
            lines.append("")
        else:
            render_blocks(child, ctx, lines, depth, indent)


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    root = (soup.find(class_="document") or soup.find(id="content")
            or soup.body or soup)
    clean_html(root)
    ctx = new_ctx(zim=zim, entry_path=entry_path)
    lines = []
    render_blocks(root, ctx, lines)
    return "`:top\n" + collapse("\n".join(lines)) + "\n"
