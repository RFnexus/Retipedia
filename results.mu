#!/bin/python3
import os
import template
import settings
import theme
import archives
from formatting import common, gutenberg
from libzim.suggestion import SuggestionSearcher

page = archives.page_root()

names = archives.available_names()
zim = os.environ.get("var_zim") or (names[0] if names else None)
if zim not in names:
    zim = None

print(template.render_header(zim))

search_query = os.environ.get("field_search_query", "")
if search_query == "":
    search_query = os.environ.get("var_search_query", "")

results_per_page = 15
try:
    current_page = max(1, min(int(os.environ.get("var_page_number", 1)), 100000))
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
        start = (current_page - 1) * results_per_page
        results = list(suggestion.getResults(start, results_per_page + 1))
        has_next = len(results) > results_per_page
        results = results[:results_per_page]
        if has_next:
            total = max(suggestion.getEstimatedMatches(), start + len(results) + 1)
        else:
            total = start + len(results)
        total_pages = max(current_page, (total + results_per_page - 1) // results_per_page)

        print(f">>{total} matches · page {current_page}/{total_pages}")
        print("")

        is_gutenberg = archives.archive_type(zim) == "gutenberg"
        if not results:
            print("No matching entries.")
        seen = set()
        shown = 0
        for path in results:
            fields = f"entry_path={path}"
            if is_gutenberg:
                listing = gutenberg.listing_fields(archive, path)
                if listing:
                    try:
                        entry_title = archive.get_entry_by_path(path).title
                    except KeyError:
                        continue
                    shown += 1
                    tag = {"author": "author", "shelf": "bookshelf"}.get(listing.split("=")[0], "index")
                    link = f"{page}/zim_index.mu`zim={zim}|{listing}"
                    print(f"{start + shown}. `F{theme.LINK}`_`[{gutenberg.label(gutenberg.book_title(entry_title))}`:{link}]`_`f `Faaa{tag}`f")
                    continue
                author = gutenberg.book_author(archive, path)
                book = gutenberg.book_path(path)
                if archive.has_entry_by_path(book):
                    path = book
                fields = gutenberg.entry_fields(path)
            if path in seen:
                continue
            seen.add(path)
            try:
                entry = archive.get_entry_by_path(path)
                size_str = common.human_size(entry.get_item().size)
            except Exception:
                continue
            shown += 1
            entry_title = entry.title
            if is_gutenberg:
                entry_title = gutenberg.label(gutenberg.book_title(entry_title) if entry_title == path else entry_title)
                if author:
                    size_str = f"{gutenberg.label(author)} · {size_str}"
            link = f"{page}/entry.mu`zim={zim}|{fields}"
            parts = link + "|chunk=parts"
            print(f"{start + shown}. `F{theme.LINK}`_`[{entry_title}`:{link}]`_`f `Faaa{size_str}`f · `F{theme.NAV}`_`[parts`:{parts}]`_`f")

        print("")
        safe_query = search_query.replace("`", "").replace("|", " ").replace("]", "")
        nav = []
        if current_page > 1:
            nav.append(f"`F{theme.NAV}`_`[◀ Previous`:{page}/results.mu`zim={zim}|search_query={safe_query}|page_number={current_page - 1}]`_`f")
        if has_next:
            nav.append(f"`F{theme.NAV}`_`[Next ▶`:{page}/results.mu`zim={zim}|search_query={safe_query}|page_number={current_page + 1}]`_`f")
        if nav:
            print("`c" + " · ".join(nav) + "`a")
