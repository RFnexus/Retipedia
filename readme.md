### 08/09/26 - Retipedia v3
- Reader adjustable text layouts
- Gutenberg .zim bookshelf support and parser fixes
- Initial StackExchange, iFixIt and MedlinePlus .zim archive support
- Initial image support
- Bug fixes

You need NomadNet 1.4.0 or newer for image rendering

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
This lets you host a [NomadNet](https://github.com/markqvist/NomadNet) node that serves searchable versions of multiple sites from .zim archives provided by the [Kiwix project](https://wiki.kiwix.org/wiki/Content_in_all_languages)

## Installation
1. Install the python-libzim package for reading .zim archives

 `pip install libzim`

2. Install the BeautifulSoup HTML parser package for converting the HTML from each .zim entry to Micron

 `pip install beautifulsoup4`

3. Move the contents of the git repo to your NomadNet `storage/pages/` directory

4. The page folder is detected automatically when the files live under `storage/pages`. You only need to adjust `root_folder` in `settings.py` for other layouts

5. Ensure all micron files for the project are executable

6. Point `zims_dir` in `settings.py` at a folder containing one or more `.zim` archives. A single `archive_path` is still supported as a fallback

7. Run `python3 generate_meta.py` once to scan the archives and write the per-archive metadata sidecars into the `zims/` folder. Re-run it whenever you add new archives. Only archives with a sidecar are listed, so delete `zims/<name>.zim.meta` to hide an archive

### Using a virtual environment (venv/conda)

The `.mu` pages start with `#!/bin/python3`, so NomadNet runs them with the system Python by default. If you installed `libzim` and `beautifulsoup4` into a virtual environment instead, pages will crash with `FileNotFoundError`. To point every page at the environment's interpreter, run this from inside that environment

 `python3 generate_meta.py --fix-shebangs`

To choose an interpreter explicitly, pass it after `=` and use quotes if it contains spaces

 `python3 generate_meta.py --fix-shebangs=/home/user/miniconda3/envs/nomad/bin/python3`

 `python3 generate_meta.py "--fix-shebangs=/usr/bin/env python3"`

To go back to the default just run it with `--fix-shebangs=/bin/python3`

### Getting .zim archives

You can download .zim archives provided by the Kiwix project here
https://browse.library.kiwix.org

The recommended .zim is `wikipedia_en_all_nopic` Wikipedia archives in every language are supported

For image support, download the `_maxi` Wikipedia instead of the `nopic` Wikipedia .zim archive

Wikipedia
https://browse.library.kiwix.org/#lang=&q=&category=wikipedia

Gutenberg
https://ebookfoundation.org/openzim.html

iFixIt
https://browse.library.kiwix.org/#lang=&q=&category=iFixit

StackExchange (all languages)
https://browse.library.kiwix.org/#lang=eng&category=stack_exchange&q=

MedlinePlus, health information from the National Institutes of Health (NIH)
https://browse.library.kiwix.org/#lang=&q=medline


Retipedia currently supports Wikipedia in all languages, Gutenberg, StackExchange in all languages, iFixIt and MedlinePlus archives, and also implements a generic .zim parser for anything else. PRs are welcome

### Image support
![A screenshot of iFixIt in Retipedia](https://rns.recipes/storage/forum/aIFyJeZtTVDmByWqQsllEvskfS2DBPxDrxS8coJu.png)
![A screenshot of Wikipedia maxi in Retipedia](https://rns.recipes/storage/forum/KFOGWWo685zqZLyptLr7NQ4n1UKoBLUBayGxZuJ2.png)
iFixIt and Wikipedia archives with pictures (maxi) can show their images in NomadNet 1.4.0 or newer on terminals with Kitty graphics support such as Konsole, iTerm2, Ghostty and Kitty. 

Set `images = True` in `settings.py` to turn it on. Readers only download images when their own NomadNet `image_loading` setting allows it, and is safe for low-bandwidth links.

Images are extracted once into the `images/` folder and served from there. You can clear that cache with

```
python3 clean_images.py        removes every extracted image
python3 clean_images.py 30     removes only images older than 30 days
```
