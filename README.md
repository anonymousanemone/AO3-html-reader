# AO3 HTML to EPUB

## Dependencies

- Python 3.8 or newer; only the Python standard library is used. No pip packages are required.
- Internet access to download externally hosted images (optional; unavailable images become links).

## Usage

Run these commands from this folder with your Python environment active. Convert an AO3 downloaded HTML/XHTML file:

```bash
python ao3_html_to_epub.py The_Lighthouse_Keeper.html
```

Creates `Title - Author.epub` beside the input. To choose a different filename:

```bash
python ao3_html_to_epub.py The_Lighthouse_Keeper.html -o new-copy.epub
```

To convert every HTML file in the current folder:

```bash
python ao3_html_to_epub.py --all
```

Existing EPUBs are skipped without overwriting. No extra packages are needed. The converter tolerates malformed HTML in AO3 downloads.

## What it preserves

- Title, authors, language, publisher, summary, source URL, and publication/update dates.
- Rating, warnings, fandoms, relationships, characters, and additional tags as searchable EPUB subjects.
- Original metadata categories, series information, statistics, chapter count, and completion status in the readable preface and/or custom metadata.
- Chapter order and titles, story text and formatting, opening/end notes, and afterword.
- Links to notes across chapters, plus a generated table of contents and chapter navigation.

PNG, JPEG, and GIF images are embedded when they can be read or downloaded. Unavailable images become labeled links to the originals, with a warning; story text is preserved. External images need network access. Designed for AO3 downloads. Reading apps vary in which metadata fields they display or search, but the original metadata remains readable in the preface.



## Read the HTML in a browser with CSS

Keep `reading.css` in the same folder as your HTML file. In a text editor, paste this one line **inside `<head>`, just before `</head>`**, after any existing `<style>` block:

```html
<link rel="stylesheet" href="reading.css" />
```

Save the HTML, then double-click it to open it in your browser (or refresh an already open tab). No server or conversion is needed. For example, adding the line to `The_Good_Mudblood.html` styles that file when opened locally.

The stylesheet adapts the downloaded AO3 styles: white background, dark content links, Georgia headings, the original Lucida Grande font stack, bordered metadata, and AO3 paragraph spacing. Horizontal gutters are reduced to 1.75% with no extra chapter inset, as requested. On small screens, metadata labels stack and margins shrink. It uses local fonts and makes no external requests. Browser zoom still works. It changes appearance only; the text, tags, notes, and links remain in the HTML. Remove the line to return to the original appearance. The HTML files have not been edited automatically.

## EPUB structure and validation

The converter produces EPUB 2 books with standard Dublin Core metadata, a separate XHTML file per chapter, a reading-order spine, an NCX table of contents, and a visible contents page. Tags use standard `dc:subject` entries; categorized source fields also use `ao3:*` metadata.

All 14 folder conversions passed checks for source text preservation, metadata, ZIP integrity, manifest references, chapter navigation, and internal links. These checks do not constitute EPUBCheck certification or visual testing in a reading app.


## Downloaded CSS references

These files were inspected locally and left unchanged. `reading.css` extracts useful rules and adapts them to AO3 download markup, which differs from a full site page. It does not import these files or make network requests.

| File | Purpose |
| --- | --- |
| `1_site_screen_.css` | Main screen stylesheet: resets, fonts, headings, links, page layout, navigation, metadata, forms, comments, story text, and work width. Source for the font stack, dark links, 25% metadata label column, line height, and paragraph spacing. |
| `4_site_midsize.handheld_.css` | Responsive overrides for screens up to 62em wide and legacy handheld media: rearranges dashboard/navigation/search and reduces work margins. |
| `5_site_narrow.handheld_.css` | Overrides up to 42em wide and legacy handheld media: mobile navigation, stacked metadata, full-width forms, filters, and smaller outer text. |
| `6_site_speech_.css` | Speech-media hints for spoken output: emphasis, voice rate, pauses, and landmark handling. Support depends on the reading software; it does not control ordinary screen rendering. |
| `7_site_print_.css` | Printing layout: serif text, compact spacing, hidden navigation/images, and URLs after some links. Does not affect normal browser display when loaded for print. |
| `sandbox.css` | Temporary site fixes and feature styling, including form fixes and social-sharing buttons. No useful story-reading rules were needed from it. |

The screenshot and downloaded styles replace the earlier unverified approximation. The body font is `100%/1.125 'Lucida Grande', 'Lucida Sans Unicode', Verdana, Helvetica, sans-serif, 'GNU Unifont'`. Story text uses AO3's combined main/work scale (0.875 × 1.08 = 0.945), a line height of 1.5, and paragraph margins of 1.286em. Fonts are fallbacks, not bundled assets; the browser uses the first installed match. Unlike the site's 72em work-width cap, the local reading style stays wide to reduce side margins.
