import re
import posixpath
from urllib.parse import unquote
from bs4 import NavigableString, Tag, Comment
import theme
import archives

RENDER_VERSION = "4"

LINK_COLOR = theme.LINK
CITE_COLOR = theme.CITE
NAV_COLOR = theme.NAV
CODE_BG = "100"
CODE_FG = "9d9"

_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")
_LINK_RE = re.compile(r"`\[([^\]]*)\]")
_STRIP_RE = re.compile(r"`[FB]T[0-9a-fA-F]{6}|`[FB][0-9a-fA-F]{3}|`:[A-Za-z0-9_\-]*|`[!*_=fbacrl`<>{]")
_TOKEN_RE = re.compile(r"(?:(?:[^\s`]|`(?!\[))*`\[[^\]]*\])+(?:[^\s`]|`(?!\[))*|\S+")
_SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+")
CONTROL_CHARS = ">-|#<"
TABLE_WIDTH = 100
CELL_MAX = 40
REF_HEADERS = {"ref", "refs", "ref.", "reference", "references", "source", "sources", "citation", "citations"}
_CITE_CELL_RE = re.compile(r"^\[\s*\d+\s*\]$")

INLINE_BOLD = {"b", "strong"}
INLINE_ITALIC = {"i", "em", "var", "dfn"}
INLINE_CODE = {"code", "kbd", "samp", "tt"}


def new_ctx(zim=None, entry_path=""):
    return {
        "root": archives.page_root(),
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
    return norm_space(text).strip().replace("`", "").replace("[", "").replace("]", "")


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
    return f"`F{LINK_COLOR}`_`[{label}`:{ctx['root']}/entry.mu`{fields}]`_`f"


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
    if isinstance(node, Comment):
        return ""
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


def cell_text(cell):
    for junk in cell.find_all("sup", class_="reference") + cell.find_all("a", class_="autonumber"):
        junk.decompose()
    value = esc(norm_space(cell.get_text(" ", strip=True)).strip()).replace("|", "/")
    if len(value) > CELL_MAX:
        value = value[:CELL_MAX - 1].rstrip() + "…"
    return value or " "


def drop_columns(rows):
    keep = []
    for c in range(len(rows[0])):
        header = rows[0][c].strip().lower()
        body = [r[c].strip() for r in rows[1:]]
        if header in REF_HEADERS or all(not b or _CITE_CELL_RE.match(b) for b in body):
            continue
        keep.append(c)
    return [[r[c] for c in keep] for r in rows] if keep else rows


def split_columns(widths, budget):
    if len(widths) <= 2 or sum(widths) + 3 * len(widths) + 1 <= budget:
        return [list(range(len(widths)))]
    groups = []
    start = 0
    while start < len(widths):
        cols = [0] if start else []
        total = sum(widths[c] + 3 for c in cols) + 1
        c = start
        while c < len(widths) and (c == start or total + widths[c] + 3 <= budget):
            cols.append(c)
            total += widths[c] + 3
            c += 1
        groups.append(cols)
        start = c
    return groups


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
            value = cell_text(cell)
            colspan = _cell_span(cell, "colspan")
            rowspan = _cell_span(cell, "rowspan")
            for dr in range(rowspan):
                for dc in range(colspan):
                    grid[(row_index + dr, col + dc)] = value if dc == 0 else " "
            col += colspan
            ncol = max(ncol, col)
        row_index += 1
    if row_index < 2 or ncol == 0:
        return
    rows = drop_columns([[grid.get((r, c), " ") for c in range(ncol)] for r in range(row_index)])
    widths = [max(3, max(len(r[c]) for r in rows)) for c in range(len(rows[0]))]
    for i, cols in enumerate(split_columns(widths, TABLE_WIDTH)):
        emit_blank(lines)
        lines.append("`t")
        lines.append("| " + " | ".join(rows[0][c] for c in cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for row in rows[1:]:
            if i and not any(row[c].strip() for c in cols[1:]):
                continue
            lines.append("| " + " | ".join(row[c] for c in cols) + " |")
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


def is_control(line):
    return line[:1] in CONTROL_CHARS or line.startswith(("`t", "`c", "`r", "`l", "`a", "`:", "`+", "`-", "`("))


def visible_width(text):
    text = _LINK_RE.sub(lambda m: m.group(1).split("`")[0], text)
    return len(_STRIP_RE.sub("", text))


def wrap_line(line, width, justify):
    rows = []
    cur = []
    cur_w = 0
    for tok in _TOKEN_RE.findall(line):
        w = visible_width(tok)
        if cur and cur_w + 1 + w > width:
            rows.append((cur, cur_w))
            cur, cur_w = [tok], w
        else:
            cur_w = cur_w + 1 + w if cur else w
            cur.append(tok)
    if cur:
        rows.append((cur, cur_w))
    out = []
    for i, (toks, w) in enumerate(rows):
        if justify and i < len(rows) - 1 and len(toks) > 1:
            gaps = len(toks) - 1
            extra = width - w
            text = "".join(tok + " " * (1 + extra // gaps + (1 if k < extra % gaps else 0))
                           for k, tok in enumerate(toks[:-1])) + toks[-1]
        else:
            text = " ".join(toks)
            if justify:
                text += " " * (width - w)
        out.append(text)
    return out


def tree_lines(items, width, prefix=""):
    out = []
    for i, (head, text, children) in enumerate(items):
        last = i == len(items) - 1
        bar = prefix + ("  " if last else "│ ")
        out.append(f"  `F888{prefix}{'└─' if last else '├─'}`f {head}")
        for row in wrap_line(text, width - len(bar), False):
            out.append(f"  `F888{bar}`f `Fbbb{row}`f")
        out.extend(tree_lines(children, width, bar))
    return out


def reflow(text, width, center=False):
    out = []
    for ln in text.split("\n"):
        if not ln.strip() or is_control(ln):
            out.append(ln)
            continue
        indent = ln[:len(ln) - len(ln.lstrip(" "))]
        if visible_width(ln) <= width:
            rows = [ln + " " * (width - visible_width(ln)) if center else ln]
        else:
            rows = [indent + row for row in wrap_line(ln.strip(), width - len(indent), center)]
        if center:
            rows = [row + "`c" for row in rows]
        out.extend(rows)
    return "\n".join(out)


def split_long(line, cap):
    if len(line.encode("utf-8")) <= cap or is_control(line):
        return [line]
    indent = line[:len(line) - len(line.lstrip(" "))]
    pieces = []
    cur = ""
    for sentence in _SENTENCE_RE.split(line.strip()):
        if cur and len(f"{cur} {sentence}".encode("utf-8")) > cap and cur.count("`[") == len(_LINK_RE.findall(cur)):
            pieces.append(indent + cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}" if cur else sentence
    if cur:
        pieces.append(indent + cur)
    return pieces


def chunk_micron(text, cap=4096):
    chunks = []
    cur = []
    size = 0
    in_table = False
    for ln in text.split("\n"):
        for i, piece in enumerate(split_long(ln, cap)):
            b = len(piece.encode("utf-8")) + 1
            is_section = piece[:2] == ">>" and piece[:3] != ">>>"
            prev_heading = bool(cur) and cur[-1].startswith(">")
            can_break = (not in_table) and bool(cur) and not prev_heading
            if can_break and (size + b > cap or (is_section and size > cap * 3 // 5)):
                chunks.append("\n".join(cur))
                cur = []
                size = 0
            if i and cur:
                cur[-1] += " " + piece.lstrip(" ")
            else:
                cur.append(piece)
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
