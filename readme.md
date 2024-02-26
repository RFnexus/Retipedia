# Retipedia - A searchable .zim wiki for NomadNet

This allows you to host a [NomadNet](https://github.com/markqvist/NomadNet) node that provides searchable version of multiple sites using .zim archives provided by the [Kiwix project](https://wiki.kiwix.org/wiki/Content_in_all_languages)

# Installation
1. Install the python-libzim package for reading .zim archives:

 `pip install libzim`
    

2. Install the BeautifulSoup HTML parser package for converting the HTML from the .zim entry to Micron

 `pip install beautifulsoup4`

3. Move the contents of the git repo to your NomadNet `storage/pages/` directory

4. Ensure all micron files for the project are executable 

5. Modify `settings.py` and configure the archive_path to point to your .zim archive

You can download .zim archives provided by the Kiwix project here:
https://wiki.kiwix.org/wiki/Content_in_all_languages





## Todo

- Allow for searching multiple .zim archives

- Add additional Micron markdown support for Wikipedia .zim archives

- Add Micron support for other .zim content

