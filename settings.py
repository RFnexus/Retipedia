# This is the root path of where the Retipedia files are contained in the .nomadnetwork storage/pages folder.
# In this example config, if your Retipedia folder is under .nomadnetwork/storage/pages/Retipedia, then the root folder would be "Retipedia"
# You can adjust htis if you want it to point at somewhere else outside of the parent folder 
root_folder = "Retipedia"

# The full path to the .zim archive 
archive_path = "" 
# What type of .zim archive the node is hosting - currently supported: wikipedia, gutenberg
archive_type = "wikipedia"

# Node settings
ascii_art_enabled = True # Do you want to print an ASCII splash at the top? (Can save a small amount of time on page load if set to "False")

node_title = "🬧 The NomadNet Encyclopedia"

# The LXMF address of the Node operator - this is an optional field that can be toggled on / off to display on the about page
lxmf_address = False
