import re
import posixpath
from urllib.parse import unquote
from bs4 import NavigableString, Tag

RENDER_VERSION = "2"

LINK_COLOR = "33f"
CITE_COLOR = "5bf"
NAV_COLOR = "0af"
CODE_BG = "100"
CODE_FG = "9d9"

_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")

INLINE_BOLD = {"b", "strong"}
INLINE_ITALIC = {"i", "em", "var", "dfn"}
INLINE_CODE = {"code", "kbd", "samp", "tt"}


def new_ctx(root, zim=None, entry_path=""):
    return {
        "root": root,
        "zim": zim,
        "entry_path": entry_path or "",
        "toc": [],
        "toc_inserted": False,
        "cite_numbers": {},
        "ref_counter": 0,
        "emitted": set(),
    }


def norm_space(text):
    return _WS_RE.sub(" ", text or "")


def esc(text):
    return (text or "").replace("\\", "\\\\").replace("`", "\\`")


def slug(text):
    return _SLUG_RE.sub("-", norm_space(text).strip()).strip("-").lower()


def clean_label(text):
    return norm_space(text).strip().replace("`", "").replace("]", "")


def guard(line):
    if line and line[0] in "#>-<":
        return "\\" + line
    return line


def resolve_path(href, ctx):
    href = (href or "").strip().split("#", 1)[0].split("?", 1)[0]
    if not href:
        return ""
    if href.startswith("/"):
        path = href.lstrip("/")
    else:
        base = posixpath.dirname(ctx.get("entry_path") or "")
        path = posixpath.normpath(posixpath.join(base, href))
    path = unquote(path).lstrip("/")
    return path.replace("`", "").replace("|", "").replace("]", "")


def entry_link(label, href, ctx):
    path = resolve_path(href, ctx)
    label = clean_label(label)
    if not path or not label:
        return esc(label)
    fields = f"entry_path={path}"
    if ctx.get("zim"):
        fields = f"zim={ctx['zim']}|" + fields
    return f"`F{LINK_COLOR}`_`[{label}`:/page/{ctx['root']}/entry.mu`{fields}]`_`f"


def anchor_link(label, target, ctx, color=None):
    label = clean_label(label)
    if not label:
        return ""
    dest = slug(target)
    if not dest:
        return esc(label)
    return f"`F{color or LINK_COLOR}`_`[{label}`#{dest}]`_`f"


def render_anchor(node, ctx):
    href = (node.get("href") or "").strip()
    classes = node.get("class") or []
    if not href:
        return render_inline(node, ctx)
    if href.startswith("#"):
        return anchor_link(node.get_text(), href[1:], ctx)
    if (href.startswith(("http://", "https://", "//", "mailto:", "tel:"))
            or "external" in classes or "extiw" in classes):
        return render_inline(node, ctx)
    return entry_link(node.get_text(), href, ctx)


def render_citation(node, ctx):
    a = node.find("a", href=True)
    if not a or not a["href"].startswith("#"):
        return ""
    target = slug(a["href"][1:])
    num = a.get_text(" ", strip=True).strip().strip("[]").strip() or "*"
    ctx["cite_numbers"][target] = num
    prefix = ""
    sup_id = node.get("id")
    if sup_id:
        s = slug(sup_id)
        ctx["emitted"].add(s)
        prefix = f"`:{s}"
    return f"{prefix}[`F{CITE_COLOR}`_`[{num}`#{target}]`_`f]"


def id_anchor(node, ctx):
    node_id = node.get("id")
    if not node_id:
        return ""
    s = slug(node_id)
    if not s:
        return ""
    ctx["emitted"].add(s)
    return f"`:{s}`a"


def render_inline_node(node, ctx):
    if isinstance(node, NavigableString):
        return esc(norm_space(str(node)))
    if not isinstance(node, Tag):
        return ""
    name = node.name
    classes = node.get("class") or []
    if name == "sup" and "reference" in classes:
        return render_citation(node, ctx)
    if name == "br":
        return "\n"
    if name in ("style", "script"):
        return ""
    if name == "a":
        content = render_anchor(node, ctx)
    elif name in INLINE_BOLD:
        inner = render_inline(node, ctx)
        content = f"`!{inner}`!" if inner.strip() else inner
    elif name in INLINE_ITALIC:
        inner = render_inline(node, ctx)
        content = f"`*{inner}`*" if inner.strip() else inner
    elif name in INLINE_CODE:
        inner = render_inline(node, ctx)
        content = f"`B{CODE_BG}`F{CODE_FG}{inner}`f`b" if inner.strip() else inner
    else:
        content = render_inline(node, ctx)
    return id_anchor(node, ctx) + content


def render_inline(node, ctx):
    return "".join(render_inline_node(child, ctx) for child in node.children)


def emit_blank(lines):
    if lines and lines[-1] != "":
        lines.append("")


def emit_text_block(lines, text):
    text = text.strip("\n")
    if not text.strip():
        return
    emit_blank(lines)
    for sub in text.split("\n"):
        sub = sub.strip()
        if sub:
            lines.append(guard(sub))
    lines.append("")


def render_list(node, ctx, lines, ordered, depth):
    emit_blank(lines)
    idx = 0
    for li in node.find_all("li", recursive=False):
        idx += 1
        sublists = []
        parts = []
        for child in li.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                sublists.append(child)
            else:
                parts.append(render_inline_node(child, ctx))
        text = norm_space("".join(parts)).strip()
        bullet = f"{idx}." if ordered else "•"
        indent = "  " * depth
        if text:
            lines.append(f"{indent}{bullet} {text}")
        for sub in sublists:
            render_list(sub, ctx, lines, sub.name == "ol", depth + 1)
    lines.append("")


def render_dl(node, ctx, lines, depth):
    emit_blank(lines)
    indent = "  " * depth
    for child in node.find_all(["dt", "dd"], recursive=False):
        text = norm_space(render_inline(child, ctx)).strip()
        if not text:
            continue
        if child.name == "dt":
            lines.append(f"{indent}`!{text}`!")
        else:
            lines.append(f"{indent}  {text}")
    lines.append("")


def render_code(node, lines):
    text = node.get_text().replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text.strip():
        return
    emit_blank(lines)
    for ln in text.split("\n"):
        lines.append(f"`B{CODE_BG}`F{CODE_FG}{esc(ln.rstrip())}`f`b")
    lines.append("")


def render_blockquote(node, ctx, lines):
    text = norm_space(render_inline(node, ctx)).strip()
    if not text:
        return
    emit_blank(lines)
    lines.append(f"  `*{text}`*")
    lines.append("")


def _cell_span(cell, attr):
    try:
        return max(1, min(int(cell.get(attr, 1)), 50))
    except (TypeError, ValueError):
        return 1


def render_table(node, ctx, lines):
    if node.find("table"):
        return
    grid = {}
    ncol = 0
    row_index = 0
    for tr in node.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        col = 0
        for cell in cells:
            while (row_index, col) in grid:
                col += 1
            value = esc(norm_space(cell.get_text(" ", strip=True)).strip())
            value = value.replace("|", "/") or " "
            colspan = _cell_span(cell, "colspan")
            rowspan = _cell_span(cell, "rowspan")
            for dr in range(rowspan):
                for dc in range(colspan):
                    grid[(row_index + dr, col + dc)] = value
            col += colspan
            ncol = max(ncol, col)
        row_index += 1
    if row_index < 2 or ncol == 0:
        return
    rows = [[grid.get((r, c), " ") for c in range(ncol)] for r in range(row_index)]
    emit_blank(lines)
    lines.append("`t")
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("|" + "|".join(["---"] * ncol) + "|")
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("`t")
    lines.append("")


def collapse(text):
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n")


def byte_size(text):
    return len((text or "").encode("utf-8"))


def human_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def chunk_micron(text, cap=4096):
    lines = text.split("\n")
    chunks = []
    cur = []
    size = 0
    in_table = False
    for ln in lines:
        b = len(ln.encode("utf-8")) + 1
        is_section = ln[:2] == ">>" and ln[:3] != ">>>"
        prev_heading = bool(cur) and cur[-1].startswith(">")
        can_break = (not in_table) and bool(cur) and not prev_heading
        if can_break and (size + b > cap or (is_section and size > cap * 3 // 5)):
            chunks.append("\n".join(cur))
            cur = []
            size = 0
        cur.append(ln)
        size += b
        if ln.strip().startswith("`t"):
            in_table = not in_table
    if cur:
        chunks.append("\n".join(cur))
    return chunks or [text]


def section_index(chunks):
    out = []
    for i, chunk in enumerate(chunks, start=1):
        for ln in chunk.split("\n"):
            if ln.startswith(">>") and not ln.startswith(">>>>"):
                level = len(ln) - len(ln.lstrip(">"))
                title = ln.lstrip(">").strip()
                if title and level in (2, 3):
                    out.append((level, title, i))
    return out
