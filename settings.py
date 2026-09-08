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
