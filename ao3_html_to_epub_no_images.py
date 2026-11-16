#!/usr/bin/env python3
"""Convert an AO3 XHTML download into an image-free EPUB 2, without overwriting files.

Uses only Python's standard library. Example:
  conda run -n general python ao3_html_to_epub_no_images.py The_Lighthouse_Keeper.html
"""
import argparse
import copy
import html.entities
from html.parser import HTMLParser
from pathlib import Path
import re
import uuid
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET
import zipfile

X = 'http://www.w3.org/1999/xhtml'
O = 'http://www.idpf.org/2007/opf'
D = 'http://purl.org/dc/elements/1.1/'
N = 'http://www.daisy.org/z3986/2005/ncx/'
NS = {'h': X}
ET.register_namespace('', X)
ET.register_namespace('dc', D)
ET.register_namespace('opf', O)
CSS = '''body { margin: 5%; line-height: 1.4; }
h1, .byline, .message { text-align: center; }
h1 { font-size: 1.6em; } h2 { font-size: 1.3em; }
dt { font-weight: bold; margin-top: .7em; } dd { margin-left: 1.2em; }
blockquote { margin: 1em; } img { max-width: 100%; height: auto; }
.toc-heading { display: none; } .endnote-link { font-size: .85em; }
'''


class AO3HTMLParser(HTMLParser):
    """Recover AO3's HTML fragments without treating void tags as containers."""
    VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ET.Element('document')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        attrs = {('{http://www.w3.org/XML/1998/namespace}lang' if k == 'xml:lang' else k): v or ''
                 for k, v in attrs if k != 'xmlns'}
        node = ET.SubElement(self.stack[-1], '{%s}%s' % (X, tag), attrs)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == '{%s}%s' % (X, tag):
                del self.stack[i:]
                break

    def handle_data(self, data):
        parent = self.stack[-1]
        if len(parent):
            parent[-1].tail = (parent[-1].tail or '') + data
        else:
            parent.text = (parent.text or '') + data


def text(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def xml(node):
    return ET.tostring(node, encoding='utf-8', xml_declaration=True)


def sub(parent, ns, tag, value=None, **attrs):
    node = ET.SubElement(parent, '{%s}%s' % (ns, tag), attrs)
    node.text = value
    return node


def read_source(path):
    source = path.read_text(encoding='utf-8-sig')
    # AO3 downloads are XHTML. Resolve HTML named entities without a network DTD.
    source = re.sub(r'<!DOCTYPE[^>]*>', '', source, flags=re.I)
    def entity(match):
        name = match[1]
        if name in {'amp', 'lt', 'gt', 'quot', 'apos'}:
            return match[0]
        value = html.entities.html5.get(name + ';')
        if value is None:
            raise ValueError('Unknown HTML entity: ' + name)
        return ''.join('&#%d;' % ord(c) for c in value)
    source = re.sub(r'&([A-Za-z][A-Za-z0-9]+);', entity, source)
    try:
        root = ET.fromstring(source)
    except ET.ParseError:
        parser = AO3HTMLParser()
        parser.feed(source)
        parser.close()
        root = parser.root.find('h:html', NS)
        if root is None:
            raise ValueError('No HTML document found')
    if root.tag != '{%s}html' % X:
        raise ValueError('Expected an AO3 XHTML download with the XHTML namespace')
    return root


def convert(source, output=None):
    root = read_source(source)
    preface = root.find('.//h:div[@id="preface"]', NS)
    chapters = root.find('.//h:div[@id="chapters"]', NS)
    if preface is None or chapters is None:
        raise ValueError('Missing AO3 preface or chapters section')
    title = text(preface.find('.//h:h1', NS))
    byline = next((e for e in preface.iter() if 'byline' in e.get('class', '').split()), preface)
    authors = list(dict.fromkeys(text(a) for a in byline.findall('.//h:a[@rel="author"]', NS)))
    if not title or not authors:
        raise ValueError('Missing work title or author')
    fields = {}
    tags = preface.find('.//h:dl[@class="tags"]', NS)
    if tags is None:
        raise ValueError('Missing AO3 metadata list')
    label = None
    for child in tags:
        if child.tag == '{%s}dt' % X:
            label = text(child).rstrip(':')
        elif child.tag == '{%s}dd' % X and label:
            fields[label] = [text(a) for a in child.findall('h:a', NS)] or [text(child)]
    stats = ' '.join(fields.get('Stats', []))
    dates = dict(re.findall(r'(Published|Updated|Completed):\s*(\d{4}-\d{2}-\d{2})', stats))
    source_url = next((a.get('href') for a in preface.iter('{%s}a' % X)
                       if re.fullmatch(r'https?://archiveofourown.org/works/\d+/?', a.get('href', ''))), None)
    language = root.get('{http://www.w3.org/XML/1998/namespace}lang') or root.get('lang') or 'en'
    summary = ''
    for parent in preface.iter():
        children = list(parent)
        for i, child in enumerate(children[:-1]):
            if child.tag == '{%s}p' % X and text(child) == 'Summary':
                summary = ET.tostring(children[i + 1], encoding='unicode')
    pages = [('preface.xhtml', 'Preface', [copy.deepcopy(preface)])]
    group = None
    chapter_count = 0
    has_headings = any(any('heading' in h.get('class', '').split()
                           for h in child.findall('h:h2', NS)) for child in chapters)
    for child in chapters if has_headings else []:
        heading = child.find('h:h2', NS)
        if heading is not None and 'heading' in heading.get('class', '').split():
            chapter_count += 1
            group = (f'chapter-{chapter_count:03}.xhtml', text(heading), [])
            pages.append(group)
        if group is None:
            if text(child):
                raise ValueError('Content before first chapter heading cannot be assigned')
        else:
            group[2].append(copy.deepcopy(child))
    if not chapter_count:
        # AO3 single-chapter downloads have no chapter header.
        pages.append(('chapter-001.xhtml', title, [copy.deepcopy(chapters)]))
        chapter_count = 1
    afterword = root.find('.//h:div[@id="afterword"]', NS)
    if afterword is not None:
        pages.append(('afterword.xhtml', 'Afterword', [copy.deepcopy(afterword)]))
    declared = re.search(r'Chapters:\s*(\d+)/(\d+|\?)', stats)
    if declared and int(declared[1]) != chapter_count:
        raise ValueError(f'Found {chapter_count} chapters, but metadata says {declared[1]}')

    id_pages = {}
    for filename, _, nodes in pages:
        for node in nodes:
            for element in node.iter():
                # Some author-written footnotes put a literal '#' in the ID/name.
                anchor = element.get('id') or (element.get('name') if element.tag == '{%s}a' % X else None)
                if anchor:
                    element.set('id', anchor.lstrip('#'))
                    if element.tag == '{%s}a' % X:
                        element.attrib.pop('name', None)
                if element.get('id'):
                    anchor = element.get('id')
                    if anchor in id_pages:
                        raise ValueError('Duplicate HTML ID: ' + anchor)
                    id_pages[anchor] = filename
    documents = {}
    for filename, heading, nodes in pages:
        doc = ET.Element('{%s}html' % X, {'lang': language, '{http://www.w3.org/XML/1998/namespace}lang': language})
        head = sub(doc, X, 'head')
        sub(head, X, 'title', heading + ' — ' + title)
        sub(head, X, 'link', rel='stylesheet', type='text/css', href='stylesheet.css')
        body = sub(doc, X, 'body')
        body.extend(nodes)
        for a in body.iter('{%s}a' % X):
            href = a.get('href', '')
            if href.startswith('#'):
                anchor = unquote(href[1:])
                if anchor not in id_pages:
                    raise ValueError('Broken source anchor: ' + href)
                a.set('href', id_pages[anchor] + '#' + quote(anchor, safe=''))
        for element in body.iter():
            if element.tag == '{%s}img' % X:
                anchor = element.get('id')
                element.tag = '{%s}span' % X
                element.attrib.clear()
                if anchor:
                    element.set('id', anchor)
                element.text = '[an image was here]'
            elif element.get('src'):
                raise ValueError('Unsupported embedded media: ' + element.get('src'))
        documents[filename] = xml(doc)

    toc = ET.Element('{%s}html' % X, {'lang': language})
    head = sub(toc, X, 'head')
    sub(head, X, 'title', 'Contents')
    sub(head, X, 'link', rel='stylesheet', type='text/css', href='stylesheet.css')
    body = sub(toc, X, 'body')
    sub(body, X, 'h1', 'Contents')
    listing = sub(body, X, 'ol')
    for filename, heading, _ in pages:
        sub(sub(listing, X, 'li'), X, 'a', heading, href=filename)
    documents['contents.xhtml'] = xml(toc)
    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, source_url or source.resolve().as_uri()))
    package = ET.Element('{%s}package' % O, {'version': '2.0', 'unique-identifier': 'book-id'})
    metadata = sub(package, O, 'metadata')
    sub(metadata, D, 'title', title)
    for author in authors:
        sub(metadata, D, 'creator', author, **{'{%s}role' % O: 'aut', '{%s}file-as' % O: author})
    sub(metadata, D, 'language', language)
    sub(metadata, D, 'identifier', uid, id='book-id', **{'{%s}scheme' % O: 'UUID'})
    sub(metadata, D, 'publisher', 'Archive of Our Own')
    if source_url:
        sub(metadata, D, 'source', source_url)
        sub(metadata, D, 'identifier', source_url, **{'{%s}scheme' % O: 'URI'})
    if summary:
        sub(metadata, D, 'description', summary)
    for kind, date in dates.items():
        sub(metadata, D, 'date', date, **{'{%s}event' % O: 'publication' if kind == 'Published' else 'modification'})
    subjects = ['Fanworks']
    for label, values in fields.items():
        if label not in {'Language', 'Stats', 'Series'}:
            subjects.extend(values)
        sub(metadata, O, 'meta', name='ao3:' + re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_'), content='; '.join(values))
    for subject in dict.fromkeys(subjects):
        sub(metadata, D, 'subject', subject)
    sub(metadata, O, 'meta', name='ao3:chapter_count', content=str(chapter_count))
    if declared:
        status = 'In progress' if declared[2] == '?' or declared[1] != declared[2] else 'Complete'
        sub(metadata, O, 'meta', name='ao3:status', content=status)
    manifest = sub(package, O, 'manifest')
    sub(manifest, O, 'item', id='ncx', href='toc.ncx', **{'media-type': 'application/x-dtbncx+xml'})
    sub(manifest, O, 'item', id='css', href='stylesheet.css', **{'media-type': 'text/css'})
    order = ['preface.xhtml', 'contents.xhtml'] + [p[0] for p in pages[1:]]
    spine = sub(package, O, 'spine', toc='ncx')
    for i, filename in enumerate(order):
        sub(manifest, O, 'item', id=f'page-{i}', href=filename, **{'media-type': 'application/xhtml+xml'})
        sub(spine, O, 'itemref', idref=f'page-{i}')
    guide = sub(package, O, 'guide')
    sub(guide, O, 'reference', type='toc', title='Contents', href='contents.xhtml')
    ncx = ET.Element('{%s}ncx' % N, {'version': '2005-1'})
    head = sub(ncx, N, 'head')
    for name, value in [('dtb:uid', uid), ('dtb:depth', '1'), ('dtb:totalPageCount', '0'), ('dtb:maxPageNumber', '0')]:
        sub(head, N, 'meta', name=name, content=value)
    sub(sub(ncx, N, 'docTitle'), N, 'text', title)
    sub(sub(ncx, N, 'docAuthor'), N, 'text', ', '.join(authors))
    nav = sub(ncx, N, 'navMap')
    for i, (filename, heading, _) in enumerate(pages, 1):
        point = sub(nav, N, 'navPoint', id=f'nav-{i}', playOrder=str(i))
        sub(sub(point, N, 'navLabel'), N, 'text', heading)
        sub(point, N, 'content', src=filename)
    container = b'''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    if output is None:
        safe = re.sub(r'[\x00-\x1f/\\:*?"<>|]', '_', title + ' - ' + ', '.join(authors))
        output = source.with_name(safe + '.epub')
    # Exclusive creation also protects against a file appearing during conversion.
    with output.open('xb') as handle:
        try:
            with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as book:
                book.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
                book.writestr('META-INF/container.xml', container)
                book.writestr('OEBPS/content.opf', xml(package))
                book.writestr('OEBPS/toc.ncx', xml(ncx))
                book.writestr('OEBPS/stylesheet.css', CSS)
                for filename, data in documents.items():
                    book.writestr('OEBPS/' + filename, data)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    return output, chapter_count, len(dict.fromkeys(subjects))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', type=Path, nargs='*', help='AO3 downloaded XHTML/HTML files')
    parser.add_argument('--all', action='store_true', help='Convert all .html/.htm files in the current folder')
    parser.add_argument('-o', '--output', type=Path, help='New EPUB path (never overwritten)')
    args = parser.parse_args()
    inputs = sorted(p for p in Path('.').iterdir() if p.suffix.lower() in {'.html', '.htm'}) if args.all else args.input
    if not inputs:
        parser.error('Provide an input file or use --all')
    if args.output and len(inputs) != 1:
        parser.error('--output requires exactly one input file')
    failed = 0
    for source in inputs:
        try:
            output, chapters, tags = convert(source, args.output)
        except FileExistsError as error:
            print(f'Skipped {source}: output already exists ({error.filename}).')
        except (OSError, ValueError, ET.ParseError) as error:
            print(f'Error converting {source}: {error}')
            failed += 1
        else:
            print(f'Created {output}: {chapters} chapters, {tags} searchable subjects.')
    if failed:
        parser.exit(1, f'{failed} conversion(s) failed.\n')


if __name__ == '__main__':
    main()
