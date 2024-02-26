#!/bin/python3
import os
# Import the template 
import template
# Import global settings 
import settings
# Import libzim
from libzim.reader import Archive
from libzim.search import Searcher, Query
from libzim.suggestion import SuggestionSearcher

### Setup ###
# Import archive_path from settings
archive_path = settings.archive_path
zim = Archive(archive_path)

# Get variables from input fields
env_string = ""
for e in os.environ:
  env_string += "{}={}\n".format(e, os.environ[e])

# Pagination setup
results_per_page = 15  
current_page = int(os.getenv('var_page_number', 1))  # Default to page 1 if not specified

### Micron Content ###
print(template.header)
search_query = os.environ.get("field_search_query", "")
if(search_query == ""):
	search_query = os.environ.get("var_search_query", "")
print(f">Searching For: {search_query}")

suggestion_searcher = SuggestionSearcher(zim)
suggestion = suggestion_searcher.suggest(search_query)
suggestion_count = suggestion.getEstimatedMatches()
total_pages = (suggestion_count + results_per_page - 1) // results_per_page  # Calculate total number of pages

print(f">>>Page {current_page} | {suggestion_count} matches for {search_query}:")

# Calculate start and end index for current page
start_index = (current_page - 1) * results_per_page
end_index = start_index + results_per_page

# Get suggestions for the current page
suggestions = list(suggestion.getResults(start_index, results_per_page))

for idx, entry_path in enumerate(suggestions, start=1):
	entry_title = zim.get_entry_by_path(entry_path).title
	print(f"{start_index + idx}. `!`[{entry_title}`:/page/entry.mu`archive_path={archive_path}|entry_path={entry_path}]`!")

# Pagination navigation
if current_page > 1:
	print(f'`F00f`_`[Previous Page`:/page/results.mu`search_query={search_query}|archive_path={archive_path}|page_number={current_page - 1}|search_query={search_query}]`_`f')
if current_page < total_pages:
	print(f'`F00f`_`[Next Page`:/page/results.mu`search_query={search_query}|archive_path={archive_path}|page_number={current_page + 1}]`_`f')
