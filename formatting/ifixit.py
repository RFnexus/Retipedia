import re
import settings
import media
from bs4 import BeautifulSoup
from formatting import generic
from formatting.common import (
    norm_space, esc, render_inline, entry_link, emit_blank, emit_text_block, collapse, new_ctx,
    tree_lines, NAV_COLOR,
)

BULLETS = {
    "bullet_red": "`Ff44•`f", "bullet_orange": "`Ffa5•`f", "bullet_yellow": "`Fff0•`f",
    "bullet_green": "`F3d3•`f", "bullet_light_blue": "`F5bf•`f", "bullet_blue": "`F33f•`f",
    "bullet_violet": "`Fa5f•`f", "icon_caution": "`Ffa5⚠`f", "icon_note": "`F5bf✎`f",
    "icon_reminder": "`F3d3⟳`f",
}
_OFFLINE_RE = re.compile(r"(external_content|unavailable_offline)\?")
_LEVEL_RE = re.compile(r"\blevel-(\d+)\b")


def text(node):
    return norm_space(node.get_text(" ", strip=True)).strip() if node else ""


def nav_line(ctx):
    return f"`F{NAV_COLOR}`_`[iFixit home`:{ctx['root']}/entry.mu`zim={ctx['zim']}|entry_path=home/home]`_`f"


def strip_offline_links(soup):
    for a in soup.find_all("a", href=_OFFLINE_RE):
        a.unwrap()


def render_body(node, ctx, lines):
    if not node:
        return
    for tag in node.find_all(["img", "svg", "script", "style", "button"]):
        tag.decompose()
    generic.render_blocks(node, ctx, lines)


def render_names(items, ctx, lines, heading):
    names = [text(p) for p in items if text(p)]
    if not names:
        return
    emit_blank(lines)
    lines.append(f">>{heading}")
    lines.append("")
    lines.extend(f"• {esc(name)}" for name in names)
    lines.append("")


def render_link_list(anchors, ctx, lines, heading, numbered=False):
    rows = []
    for a in anchors:
        label = text(a.find(["h4", "h5", "p"]) or a)
        if a.get("href") and label:
            blurb = text(a.find("p")) if a.find(["h4", "h5"]) else ""
            rows.append((entry_link(label, a["href"], ctx), blurb))
    if not rows:
        return
    emit_blank(lines)
    lines.append(f">>{heading}")
    lines.append("")
    for i, (link, blurb) in enumerate(rows, start=1):
        line = f"{i}. {link}" if numbered else f"• {link}"
        if blurb:
            line += f" `Faaa{esc(blurb)}`f"
        lines.append(line)
    lines.append("")


def comment_entries(container, ctx):
    entries = []
    for thread in container.select(".comment-thread"):
        info = thread.find(class_="comment-info")
        if not info:
            continue
        top = info.find(class_="comment", recursive=False)
        replies = [r.find(class_="comment") for r in info.find_all(class_="comment-reply", recursive=False)]
        if top:
            entries.append(comment_entry(top, ctx, [comment_entry(r, ctx, []) for r in replies if r]))
    return entries


def comment_entry(node, ctx, children):
    meta = node.find(class_="commentMeta")
    user = text(meta.find("a")) if meta and meta.find("a") else "anonymous"
    when = text(meta.find("time")) if meta else ""
    head = f"`!{esc(user)}`!" + (f" `F888· {esc(when)}`f" if when else "")
    body = node.find(class_="commentContent")
    content = norm_space(render_inline(body, ctx)).strip() if body else ""
    return (head, content, children)


def render_comments(entries, lines, depth):
    if not entries:
        return
    total = len(entries) + sum(len(e[2]) for e in entries)
    emit_blank(lines)
    lines.append(f"`-{'>' * depth}{total} {'comment' if total == 1 else 'comments'}")
    lines.extend(tree_lines(entries, getattr(settings, "text_width", 72) - 3))
    lines.append("<")
    lines.append("")


def render_image(node, alt, ctx, lines, align="c"):
    img = node.find("img", src=True) if node else None
    tag = media.image_tag(img["src"], alt, ctx, align=align) if img else ""
    if tag:
        emit_blank(lines)
        lines.append(tag)
        lines.append("")


def render_steps(soup, ctx, lines):
    for step in soup.select("li.step-wrapper"):
        title = text(step.select_one(".step-title"))
        emit_blank(lines)
        lines.append(f">>{esc(title) or 'Step'}")
        lines.append("")
        render_image(step.select_one(".step-main-media"), title or "Step image", ctx, lines, align="l")
        for li in step.select(".step-lines > li"):
            classes = " ".join(li.get("class") or [])
            m = _LEVEL_RE.search(classes)
            indent = "  " * (int(m.group(1)) if m else 0)
            bullet = li.find(class_="bullet")
            marker = next((BULLETS[c] for c in (bullet.get("class") or []) if c in BULLETS), "•") if bullet else "•"
            content = " ".join(norm_space(render_inline(p, ctx)).strip() for p in li.find_all("p", recursive=False))
            if content:
                lines.append(f"{indent}{marker} {content}")
        lines.append("")
        render_comments(comment_entries(step, ctx), lines, 3)


def render_guide(soup, ctx, lines):
    meta = []
    author = soup.select_one(".guide-author a")
    if author and author.get("href"):
        meta.append("by `f" + entry_link(text(author), author["href"], ctx) + "`Faaa")
    published = text(soup.select_one(".guide-published-date"))
    if published:
        meta.append(published)
    for item in soup.select(".guide-details-container .details-item"):
        label, value = text(item.find(class_="item-title")), text(item.find(class_="item-value"))
        if label and value:
            meta.append(f"{label}: {value}")
    count = text(soup.select_one(".comments-count .stats-value"))
    if count:
        meta.append(f"{count} comments")
    if meta:
        lines.append("`Faaa" + " · ".join(meta) + "`f")
        lines.append("")
    render_image(soup.select_one(".guide-main-image"), text(soup.select_one(".guide-title")), ctx, lines)
    render_body(soup.select_one(".introduction-container [itemprop=description]"), ctx, lines)
    render_names(soup.select(".item-list-tools .attachment-link .title"), ctx, lines, "Tools")
    render_names(soup.select(".item-list-parts .attachment-link .title"), ctx, lines, "Parts")
    render_steps(soup, ctx, lines)
    conclusion = soup.select_one("#conclusion .conclusionText")
    if conclusion and text(conclusion):
        emit_blank(lines)
        lines.append(">>Conclusion")
        lines.append("")
        render_body(conclusion, ctx, lines)
    comments = soup.select_one("#comments")
    entries = comment_entries(comments, ctx) if comments else []
    hidden = soup.find(id=re.compile(r"^hidden-main-comments"))
    if hidden:
        entries += comment_entries(hidden, ctx)
    render_comments(entries, lines, 2)


def render_device(soup, ctx, lines):
    render_image(soup.select_one(".banner-small-photo"), text(soup.select_one(".banner-title")), ctx, lines)
    blurb = text(soup.select_one(".banner-blurb"))
    if blurb:
        emit_text_block(lines, esc(blurb))
    render_link_list(soup.select(".categoryListCell a.categoryAnchor"), ctx, lines, "Categories")
    render_link_list(soup.select(".highlight-guides a.entry"), ctx, lines, "Featured guides", numbered=True)
    for section in soup.select(".blurbListWide"):
        render_link_list(section.select(".cell a.title"), ctx, lines, text(section.find("h3")) or "Guides", numbered=True)
    render_names(soup.select("#Section_tools_and_parts .attachment-link .title"), ctx, lines, "Tools")
    render_body(soup.find(id="wikiRenderedText"), ctx, lines)


def render_user(soup, ctx, lines):
    info = [text(soup.find(id="unique-username"))]
    rep = text(soup.find(id="numReputation"))
    if rep:
        info.append(f"{rep} reputation")
    since = text(soup.find(class_="memberSince"))
    if since:
        info.append(f"member since {since}")
    lines.append("`Faaa" + esc(" · ".join(i for i in info if i)) + "`f")


def render_home(soup, ctx, lines):
    heading = text(soup.select_one(".homepage-top h1"))
    if heading:
        emit_text_block(lines, esc(heading))
    render_link_list(soup.select("a.featured-category-item"), ctx, lines, "Featured categories")
    subs = soup.select("a.sub-category")
    if subs:
        emit_blank(lines)
        lines.append(">>All categories")
        lines.append("")
        for a in subs:
            label = text(a.select_one(".sub-category-title-text"))
            count = text(a.select_one(".overflow-slide-in"))
            if a.get("href") and label:
                line = f"• {entry_link(label, a['href'], ctx)}"
                if count:
                    line += f" `Faaa{esc(count)}`f"
                lines.append(line)
        lines.append("")


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    ctx = new_ctx(zim=zim, entry_path=entry_path)
    strip_offline_links(soup)
    lines = ["`:top", nav_line(ctx), ""]
    if soup.find(id="guide-intro"):
        render_guide(soup, ctx, lines)
    elif soup.find(class_="banner-title") or soup.find(class_="blurbListWide"):
        render_device(soup, ctx, lines)
    elif soup.find(id="aboutBox"):
        render_user(soup, ctx, lines)
    elif soup.find(class_="featured-categories"):
        render_home(soup, ctx, lines)
    else:
        summary = text(soup.select_one("p.summary"))
        if summary:
            emit_text_block(lines, esc(summary))
        render_body(soup.find(id="wikiRenderedText") or soup.find(id="content") or soup.body or soup, ctx, lines)
    return collapse("\n".join(lines)) + "\n"
