# This is the root path of where the Retipedia files are contained in the .nomadnetwork storage/pages folder.
# In this example config, if your Retipedia folder is under .nomadnetwork/storage/pages/Retipedia, then the root folder would be "Retipedia"
# Set this to None (or "") if the Retipedia files live directly in storage/pages with no subfolder
root_folder = "Retipedia"

# Directory containing one or more .zim archives to host. When set, Retipedia lists
# every .zim in this folder on the index page. Run generate_meta.py once after adding
# archives to create the per-archive metadata sidecars in the zims/ subfolder.
# It must be an absolute path, like ~/myzims or /home/myuser/myzims
zims_dir = ""

# Optional single-archive fallback used when zims_dir is empty or unset.
archive_path = ""
# What type of .zim archive the single-archive fallback is - currently supported: wikipedia, gutenberg, ifixit, stackexchange, medlineplus, generic
archive_type = "wikipedia"

# Target size in bytes for each part when a reader chooses "Read in parts" on a large
# entry. Smaller values transfer faster per request but make more parts; lower this
# (e.g. 2048) for very slow HF links, raise it for faster connections.
chunk_size = 4096

# Default text layout for entries, options: center, wide, narrow. Optionally specify text width
# This can be selected by the reader
text_layout = "wide"
text_width = 72

# How long (in seconds) readers NomadNet clients may keep an entry page cached before fetching it again
page_cache = 604800	

# Show images from archives that support them (currently iFixit and Wikipedia maxi zims that have images)
# You need NomadNet >1.4.0 for this
# and a terminal emulator that supports the kitty graphics protocol on the client end, like Konsole, Ghostty, iTerm2, or Kitty
images = False

# EPUB downloads for Gutenberg books (off by default). Adds a ⤓ EPUB link to
# book pages, search results and the bookshelf. The EPUB is copied out of the
# .zim on first request (or built from the book's HTML if the archive has no
# EPUBs) into NomadNet's storage/files folder, and served from there.
epub_enabled = False
# epub_files_dir = None     # override NomadNet's storage/files path
# epub_subfolder = "books"  # subfolder inside storage/files
# epub_cache_mb = 2048      # size budget for extracted EPUBs; 0 = unlimited
# epub_refresh_min = 1      # should match NomadNet's file_refresh_interval
# epub_fallback = True      # build a simple EPUB from the HTML if the zim has none
# epub_instant_refresh = False  # True only if NomadNet registers new files instantly

# Accent color for the interface (ascii header, links, navigation, citations)
# Options: "default" (blue), "red", "orange", "green"
accent_color = "default"

# Node settings
ascii_art_enabled = True # Do you want to print an ASCII splash at the top? (Can save a small amount of time on page load if set to "False")

node_title = "🬧 The NomadNet Encyclopedia"

# The LXMF address of the Node operator - this is an optional field that can be toggled on / off to display on the about page
lxmf_address = False

# or:
# lxmf_address = "your LXMF hash here"