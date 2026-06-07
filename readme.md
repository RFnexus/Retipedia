### 07/06/26 - Retipedia V2
- Formatting overhaul to add anchors, tables, inline citations and better page layouts
- Support for multiple .zim archives
- Add full Gutenberg parser
- Parser improvements
- Server-side caching
- Option to read pages in sections for low-bandwidth users 
- And more

# Retipedia - A searchable .zim wiki for NomadNet
![A screenshot of Retipedia running in NomadNet](https://i.ibb.co/pvZsdfTV/Screenshot-from-2026-06-07-06-10-18.png)
This allows you to host a [NomadNet](https://github.com/markqvist/NomadNet) node that provides searchable version of multiple sites using .zim archives provided by the [Kiwix project](https://wiki.kiwix.org/wiki/Content_in_all_languages)

## Installation
1. Install the python-libzim package for reading .zim archives:

 `pip install libzim`
    

2. Install the BeautifulSoup HTML parser package for converting the HTML from the .zim entry to Micron

 `pip install beautifulsoup4`

3. Move the contents of the git repo to your NomadNet `storage/pages/` directory

4. Adjust root_folder in `settings.py` to where the page files for Retipedia are located

5. Ensure all micron files for the project are executable 

6. Point `zims_dir` in `settings.py` at a folder containing one or more `.zim` archives (a single `archive_path` is still supported as a fallback)

7. Run `python3 generate_meta.py` once to scan the archives and write the per-archive metadata sidecars into the `zims/` folder. Re-run it whenever you add new archives.

You can download .zim archives provided by the Kiwix project here:
https://browse.library.kiwix.org

The recommended .zim is `#wikipedia_en_all_nopic_2026-03` https://browse.library.kiwix.org/viewer#wikipedia_en_all_nopic_2026-03/User%3AThe_other_Kiwix_guy/Landing which provides 7,155,441 articles in English 

Recommended Gutenberg .zim: https://ebookfoundation.org/openzim.html

Retipedia currently supports all language Wikipedia .zim archives, Gutenberg .zim archives, and also implements a generic .zim parser for anything else. PRs are welcome



