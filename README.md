# Rendering AO3 HTML 

You can convert your HTML file to EPUB with metadata preserved, using a python script.
OR
You can read the HTML file with better formatting using custom CSS.

## HTML to EPUB conversion

Run these commands from this folder with your Python environment active. No pip packages required. 

To create `Title - Author.epub`: 
```
python ao3_html_to_epub.py The_Lighthouse_Keeper.html
```

To choose a different filename:

```
python ao3_html_to_epub.py The_Lighthouse_Keeper.html -o new-copy.epub
```

To convert every HTML file in the current folder:

```
python ao3_html_to_epub.py --all
```

Existing EPUBs are skipped without overwriting. No extra packages are needed. The converter tolerates malformed HTML in AO3 downloads.


## Read the HTML in a browser with CSS

Keep `reading.css` in the same folder as your HTML file. In a text editor, paste this one line **inside `<head>`, just before `</head>`**, after any existing `<style>` block:

```html
<link rel="stylesheet" href="reading.css" />
```

Save the HTML, then double-click it to open it in your browser (or refresh an already open tab). No server or conversion is needed. The stylesheet AO3 stylesheets. 

## Additional Information

### Preserved Information

- Title, authors, language, publisher, summary, source URL, and publication/update dates.
- Rating, warnings, fandoms, relationships, characters, and additional tags as searchable EPUB subjects.
- Original metadata categories, series information, statistics, chapter count, and completion status in the readable preface and/or custom metadata.
- Chapter order and titles, story text and formatting, opening/end notes, and afterword.
- Links to notes across chapters, plus a generated table of contents and chapter navigation.

PNG, JPEG, and GIF images are embedded when they can be read or downloaded. Unavailable images become labeled links to the originals, with a warning; story text is preserved. External images need network access. Designed for AO3 downloads. Reading apps vary in which metadata fields they display or search, but the original metadata remains readable in the preface.

### Dependencies

- Python 3.8 or newer; only the Python standard library is used. No pip packages are required.
- Internet access to download externally hosted images (optional; unavailable images become links).