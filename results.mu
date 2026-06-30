#!/bin/python3
import os
import template
import settings
import theme
import archives
from formatting import common, gutenberg
from libzim.suggestion import SuggestionSearcher

rf = settings.root_folder
page = f"/page/{rf}" if rf else "/page"

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)

print(template.render_header(zim))

search_query = os.environ.get("field_search_query", "")
if search_query == "":
    search_query = os.environ.get("var_search_query", "")

results_per_page = 15
try:
    current_page = max(1, int(os.environ.get("var_page_number", 1)))
except ValueError:
    current_page = 1

if not zim:
    print(">No archive selected")
    print(f"`F{theme.LINK}`_`[Choose an archive`:{page}/index.mu]`_`f")
else:
    archive = archives.open_archive(zim)
    title = archives.load_meta(zim).get("title", zim)
    print(f">Search: {search_query}")
    print(f"`Faaain {title}`f")
    print("")

    if not search_query.strip():
        print("Type a query in the search field above.")
    else:
        searcher = SuggestionSearcher(archive)
        suggestion = searcher.suggest(search_query)
        total = suggestion.getEstimatedMatches()
        total_pages = max(1, (total + results_per_page - 1) // results_per_page)
        current_page = min(current_page, total_pages)
        start = (current_page - 1) * results_per_page

        print(f">>{total} matches · page {current_page}/{total_pages}")
        print("")

        results = list(suggestion.getResults(start, results_per_page))
        is_gutenberg = archives.archive_type(zim) == "gutenberg"
        if not results:
            print("No matching entries.")
        seen = set()
        shown = 0
        for path in results:
            if is_gutenberg:
                path = gutenberg.book_path(path)
            if path in seen:
                continue
            seen.add(path)
            try:
                entry = archive.get_entry_by_path(path)
                size_str = common.human_size(entry.get_item().size)
            except Exception:
                continue
            shown += 1
            link = f"{page}/entry.mu`zim={zim}|entry_path={path}"
            parts = link + "|chunk=parts"
            print(f"{start + shown}. `F{theme.LINK}`_`[{entry.title}`:{link}]`_`f `Faaa{size_str}`f · `F{theme.NAV}`_`[parts`:{parts}]`_`f")

        print("")
        safe_query = search_query.replace("`", "").replace("|", " ").replace("]", "")
        nav = []
        if current_page > 1:
            nav.append(f"`F{theme.NAV}`_`[◀ Previous`:{page}/results.mu`zim={zim}|search_query={safe_query}|page_number={current_page - 1}]`_`f")
        if current_page < total_pages:
            nav.append(f"`F{theme.NAV}`_`[Next ▶`:{page}/results.mu`zim={zim}|search_query={safe_query}|page_number={current_page + 1}]`_`f")
        if nav:
            print("`c" + " · ".join(nav) + "`a")
