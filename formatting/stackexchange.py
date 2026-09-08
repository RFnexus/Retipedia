import re
import settings
from bs4 import BeautifulSoup, Tag
from formatting import generic
from formatting.common import (
    norm_space, esc, render_inline, entry_link, emit_blank, collapse, new_ctx, tree_lines, NAV_COLOR,
)

NAV_PAGES = [("Questions", "questions"), ("Tags", "tags"), ("Users", "users")]
_VIEWED_RE = re.compile(r"^Viewed ")


def text(node):
    return norm_space(node.get_text(" ", strip=True)).strip() if node else ""


def page_link(label, path, ctx):
    return f"`F{NAV_COLOR}`_`[{label}`:{ctx['root']}/entry.mu`zim={ctx['zim']}|entry_path={path}]`_`f"


def nav_line(ctx):
    return " · ".join(page_link(label, path, ctx) for label, path in NAV_PAGES)


def render_body(node, ctx, lines):
    if not node:
        return
    for tag in node.find_all(["img", "svg", "script", "style"]):
        tag.decompose()
    generic.render_blocks(node, ctx, lines)


def by_line(post, ctx, verb):
    cell = post.find(class_="postcell") or post
    cards = cell.find_all(class_="s-user-card")
    card = next((c for c in cards if text(c.find("time")).startswith(verb)), cards[-1] if cards else None)
    if not card:
        return ""
    when = text(card.find("time"))
    user = card.find("a", class_="s-user-card--link")
    line = esc(when or verb)
    if user and user.get("href"):
        line += " by `f" + entry_link(text(user), user["href"], ctx)
    return line


def render_comments(post, ctx, lines, depth):
    items = [li for li in post.select("li.comment") if li.find(class_="comment-copy")]
    if not items:
        return
    entries = []
    for li in items:
        user = text(li.find(class_="comment-user")) or "anonymous"
        meta = [text(li.find(class_="relativetime-clean"))]
        score = li.get("data-comment-score", "0")
        if score not in ("", "0"):
            meta.append(f"▲ {score}")
        head = f"`!{esc(user)}`! `F888· {esc(' · '.join(m for m in meta if m))}`f"
        content = norm_space(render_inline(li.find(class_="comment-copy"), ctx)).strip()
        entries.append((head, content, []))
    emit_blank(lines)
    lines.append(f"`-{'>' * depth}{len(items)} {'comment' if len(items) == 1 else 'comments'}")
    lines.extend(tree_lines(entries, getattr(settings, "text_width", 72) - 3))
    lines.append("<")
    lines.append("")


def render_question(soup, ctx, lines):
    q = soup.find(id="question")
    meta = [f"▲ {q.get('data-score', '0')}"]
    viewed = soup.find(attrs={"title": _VIEWED_RE})
    if viewed:
        meta.append(esc(text(viewed).lower()))
    by = by_line(q, ctx, "asked")
    if by:
        meta.append(by)
    lines.append("`Faaa" + " · ".join(meta) + "`f")
    lines.append("")
    render_body(q.find(class_="js-post-body"), ctx, lines)
    tags = [entry_link(text(a), a["href"], ctx) for a in q.select(".post-taglist a.post-tag") if a.get("href")]
    if tags:
        emit_blank(lines)
        lines.append("`Faaatags:`f " + " ".join(tags))
        lines.append("")
    render_comments(q, ctx, lines, 2)
    answers = soup.select("div.answer")
    if not answers:
        emit_blank(lines)
        lines.append(">>No answers yet")
        return
    emit_blank(lines)
    lines.append(f">>{len(answers)} {'answer' if len(answers) == 1 else 'answers'}")
    lines.append("")
    for i, ans in enumerate(answers, start=1):
        head = f"Answer {i} · ▲ {ans.get('data-score', '0')}"
        if "accepted-answer" in (ans.get("class") or []):
            head += " · ✔ accepted"
        emit_blank(lines)
        lines.append(f">>>{head}")
        by = by_line(ans, ctx, "answered")
        if by:
            lines.append(f"`Faaa{by}`f")
        lines.append("")
        render_body(ans.find(class_="js-post-body"), ctx, lines)
        render_comments(ans, ctx, lines, 4)


def render_pager(soup, ctx, lines):
    pager = soup.find(class_="s-pagination")
    if not pager:
        return
    parts = []
    for el in pager.children:
        if not isinstance(el, Tag):
            continue
        label = text(el)
        if not label:
            continue
        if el.name == "a" and el.get("href"):
            parts.append(entry_link(label, el["href"], ctx))
        elif "is-selected" in (el.get("class") or []):
            parts.append(f"`!{esc(label)}`!")
        else:
            parts.append(esc(label))
    if parts:
        emit_blank(lines)
        lines.append("`c" + " · ".join(parts) + "`a")


def render_listing(soup, ctx, lines):
    excerpt = soup.find(id="wiki-excerpt")
    if excerpt and text(excerpt):
        lines.append(esc(text(excerpt)))
        lines.append("")
    count = soup.find(class_="fs-body3")
    if count and "question" in text(count):
        lines.append(f"`Faaa{esc(text(count))}`f")
        lines.append("")
    for i, item in enumerate(soup.select("div.question-summary"), start=1):
        a = item.select_one("a.question-hyperlink")
        if not a or not a.get("href"):
            continue
        status = item.select_one(".status")
        answers = text(status.find("strong")) if status else ""
        info = [f"▲ {text(item.select_one('.vote-count-post')) or '0'}"]
        if answers:
            info.append(f"{answers} {'answer' if answers == '1' else 'answers'}"
                        + (" ✔" if "answered-accepted" in (status.get("class") or []) else ""))
        tags = [text(t) for t in item.select("a.post-tag")]
        if tags:
            info.append(", ".join(tags))
        when = text(item.select_one(".s-user-card--time"))
        user = text(item.select_one(".s-user-card--link"))
        if when:
            info.append(when + (f" by {user}" if user else ""))
        lines.append(f"{i}. {entry_link(text(a), a['href'], ctx)}")
        lines.append("   `Faaa" + esc(" · ".join(info)) + "`f")
    render_pager(soup, ctx, lines)


def render_tags(soup, ctx, lines):
    for i, card in enumerate(soup.select(".js-tag-cell"), start=1):
        a = card.find("a", class_="post-tag")
        if not a or not a.get("href"):
            continue
        line = f"{i}. {entry_link(text(a), a['href'], ctx)}"
        count = card.select_one(".fs-caption")
        if count:
            line += f" `Faaa{esc(text(count))}`f"
        lines.append(line)
        desc = text(card.find(class_="v-truncate4"))
        if desc:
            lines.append(f"   {esc(desc)}")
    render_pager(soup, ctx, lines)


def render_users(soup, ctx, lines):
    for i, info in enumerate(soup.select(".user-info"), start=1):
        a = info.select_one(".user-details a")
        if not a or not a.get("href"):
            continue
        line = f"{i}. {entry_link(text(a), a['href'], ctx)}"
        rep = info.select_one(".reputation-score")
        if rep:
            line += f" `Faaa{esc(text(rep))} reputation`f"
        lines.append(line)
    render_pager(soup, ctx, lines)


def render_user(soup, ctx, lines):
    card = soup.find(id="user-card")
    info = []
    rep = card.select_one(".fs-title")
    if rep:
        info.append(f"{text(rep)} reputation")
    info += [text(li) for li in card.select(".metadata-box li") if text(li)]
    if info:
        lines.append("`Faaa" + esc(" · ".join(info)) + "`f")
        lines.append("")
    render_body(soup.find(class_="profile-user--bio"), ctx, lines)


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    ctx = new_ctx(zim=zim, entry_path=entry_path)
    lines = ["`:top", nav_line(ctx), ""]
    if soup.find(id="question"):
        render_question(soup, ctx, lines)
    elif soup.select_one("div.question-summary") or soup.find(id="questions"):
        render_listing(soup, ctx, lines)
    elif soup.find(id="tags-browser"):
        render_tags(soup, ctx, lines)
    elif soup.find(id="user-browser"):
        render_users(soup, ctx, lines)
    elif soup.find(id="user-card"):
        render_user(soup, ctx, lines)
    else:
        content = soup.find(id="content") or soup.body or soup
        generic.clean_html(content)
        generic.render_blocks(content, ctx, lines)
    return collapse("\n".join(lines)) + "\n"
