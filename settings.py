# This is the root path of where the Retipedia files are contained in the .nomadnetwork storage/pages folder.
# In this example config, if your Retipedia folder is under .nomadnetwork/storage/pages/Retipedia, then the root folder would be "Retipedia"
# You can adjust this if you want it to point at somewhere else outside of the parent folder
root_folder = "Retipedia"

# Directory containing one or more .zim archives to host. When set, Retipedia lists
# every .zim in this folder on the index page. Run generate_meta.py once after adding
# archives to create the per-archive metadata sidecars in the zims/ subfolder.
zims_dir = ""

# Optional single-archive fallback used when zims_dir is empty or unset.
archive_path = ""
# What type of .zim archive the single-archive fallback is - currently supported: wikipedia, generic
archive_type = "wikipedia"

# Target size in bytes for each part when a reader chooses "Read in parts" on a large
# entry. Smaller values transfer faster per request but make more parts; lower this
# (e.g. 2048) for very slow HF links, raise it for faster connections.
chunk_size = 4096

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
