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
from formatting import wikipedia

# Get variables from input field 
env_string = ""
for e in os.environ:
  env_string += "{}={}\n".format(e, os.environ[e])

archive_path = os.environ['var_archive_path']
entry_path = os.environ['var_entry_path']

archive = Archive(archive_path)

try:
    entry = archive.get_entry_by_path(entry_path)
    entry_title = entry.title
    item = entry.get_item()
    content = bytes(item.content)
    text_content = content.decode('utf-8')
    
    # Header
    print(template.header)

    
    # Main content
    print(f">{entry_title}")
    # Convert the Wikipedia HTML formatting contained within the .zim to Micron
    micron_content = wikipedia.html_to_micron(text_content)
    print(micron_content)
    
except KeyError:  
    print(template.header)
    print("Can't find entry")
