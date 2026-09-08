from bs4 import BeautifulSoup
from formatting import generic
from formatting.common import norm_space, esc, collapse, new_ctx, NAV_COLOR

NAV_PAGES = [("Home", "medlineplus.gov/"), ("Health topics", "medlineplus.gov/healthtopics.html"),
             ("Encyclopedia", "medlineplus.gov/encyclopedia.html"),
             ("Drugs", "medlineplus.gov/druginformation.html"), ("Genetics", "medlineplus.gov/genetics/"),
             ("Lab tests", "medlineplus.gov/lab-tests/")]
REMOVE_TAGS = ["script", "style", "noscript", "form", "button", "img", "svg", "iframe"]
REMOVE_IDS = ["breadcrumbs", "toc-section", "toc-box", "citation-how-to", "mplus-footer"]
REMOVE_CLASSES = ["print-only", "page-actions", "section-button", "sm-live-area", "hide-offscreen",
                  "ency-citation", "adam-info", "provider-box", "icon", "js-disabled-message",
                  "page-title", "share-links"]


def nav_line(ctx):
    return " · ".join(f"`F{NAV_COLOR}`_`[{label}`:{ctx['root']}/entry.mu`zim={ctx['zim']}|entry_path={path}]`_`f"
                      for label, path in NAV_PAGES)


def html_to_micron(html_content, zim=None, entry_path=""):
    soup = BeautifulSoup(html_content, "html.parser")
    ctx = new_ctx(zim=zim, entry_path=entry_path)
    root = soup.find(id="mplus-content") or soup.body or soup
    lines = ["`:top", nav_line(ctx), ""]
    also = root.find(class_="alsocalled")
    if also and norm_space(also.get_text(" ", strip=True)).strip():
        lines.append(f"`Faaa{esc(norm_space(also.get_text(' ', strip=True)).strip())}`f")
        lines.append("")
    for tag in root.find_all(REMOVE_TAGS):
        tag.decompose()
    for el_id in REMOVE_IDS:
        el = root.find(id=el_id)
        if el:
            el.decompose()
    for cls in REMOVE_CLASSES:
        for el in root.find_all(class_=cls):
            el.decompose()
    generic.render_blocks(root, ctx, lines)
    return collapse("\n".join(lines)) + "\n"
