"""Pinned local SVG catalogue and safe vector conversion for LaTeX."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

DIRECTORY = Path(__file__).resolve().parents[1] / 'assets/logos'
TOKEN = re.compile(r'!\[logo:([a-z0-9][a-z0-9-]{0,63})(?:@([0-9]+(?:\.[0-9]+)?))?\]')


def catalogue():
    data = json.loads((DIRECTORY / 'manifest.json').read_text(encoding='utf-8'))
    items = list(data['icons'])
    if (DIRECTORY / 'local').is_symlink():
        raise ValueError('Local logo directory cannot be a symlink')
    local_manifest = DIRECTORY / 'local/manifest.json'
    if local_manifest.exists():
        if local_manifest.is_symlink():
            raise ValueError('Local logo manifest cannot be a symlink')
        local_items = json.loads(local_manifest.read_text(encoding='utf-8'))['icons']
        for entry in local_items:
            entry['local'] = True
            entry['storage'] = 'local'
        items.extend(local_items)
    custom_dir = DIRECTORY / 'custom'
    if custom_dir.is_dir() and not custom_dir.is_symlink():
        for path in sorted(custom_dir.glob('*.svg')):
            if path.is_symlink():
                continue
            slug = path.stem.lower()
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', slug):
                continue
            try:
                raw = path.read_bytes()
                validate_svg(raw)
            except Exception:
                continue
            items.append({
                'id': slug,
                'name': slug.replace('-', ' ').title(),
                'file': path.name,
                'category': 'custom',
                'storage': 'custom',
                'sha256': hashlib.sha256(raw).hexdigest(),
                'custom': True,
                'local': True
            })
    result = {}
    for item in items:
        slug, filename = item['id'], item['file']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', slug) or filename != slug + '.svg':
            raise ValueError('Invalid logo catalogue entry')
        if item.get('storage', 'bundled') not in {'bundled', 'schools', 'local', 'custom'}:
            raise ValueError('Invalid logo storage')
        if slug in result:
            if item.get('local') and not result[slug].get('local'):
                continue  # Published material wins over a legacy private download.
            raise ValueError('Duplicate logo catalogue entry')
        result[slug] = item
    return result


def resolve_logo_path(filename):
    """Resolve only registered filenames, without following paths outside the catalogue."""
    for item in catalogue().values():
        if item['file'] == filename:
            storage = item.get('storage', 'local' if item.get('local') else 'bundled')
            directory = DIRECTORY if storage == 'bundled' else DIRECTORY / storage
            path = directory / filename
            if directory.is_symlink() or path.is_symlink() or path.resolve().parent != directory.resolve():
                raise ValueError('Logo path escapes its catalogue')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise ValueError('Logo checksum mismatch')
            validate_svg(raw)
            return path
    raise ValueError('Unknown logo file')


def validate_svg(data):
    if len(data) > 500_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('SVG is too large or contains a DTD/entity')
    root = ET.fromstring(data)
    allowed = {'svg', 'title', 'desc', 'path', 'g', 'circle', 'rect', 'ellipse', 'line', 'polyline', 'polygon'}
    if root.tag.rsplit('}', 1)[-1] != 'svg':
        raise ValueError('Expected an SVG root')
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] not in allowed:
            raise ValueError('Unsupported SVG element')
        for key, value in element.attrib.items():
            key = key.rsplit('}', 1)[-1].lower()
            if key.startswith('on') or key in {'href', 'src', 'style'} or re.search(r'url\s*\(|javascript:|https?:|file:|data:|@import', value, re.I):
                raise ValueError('SVG active content or external references are not allowed')
    return root


def prepare(slugs, output):
    if not slugs:
        return
    import fitz
    entries = catalogue()
    target = Path(output) / 'logos'
    target.mkdir(parents=True, exist_ok=True)
    used = []
    for slug in sorted(set(slugs)):
        if slug not in entries:
            raise ValueError(f'Unknown logo: {slug}; see references/logos.md')
        item = entries[slug]
        data = resolve_logo_path(item['file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f'Logo checksum mismatch: {slug}')
        validate_svg(data)
        with fitz.open(stream=data, filetype='svg') as document:
            (target / (slug + '.pdf')).write_bytes(document.convert_to_pdf())
        # Keep the editable vector and provenance with every delivered resume.
        (target / item['file']).write_bytes(data)
        used.append(item)
    for name in ['LICENSE.simple-icons.md', 'DISCLAIMER.simple-icons.md']:
        (target / name).write_bytes((DIRECTORY / name).read_bytes())
    if any(item.get('storage') == 'schools' for item in used):
        for name in ['SOURCES.json', 'RIGHTS.md', 'LICENSE.upstream-collection.txt']:
            (target / ('SCHOOL-' + name)).write_bytes((DIRECTORY / 'schools' / name).read_bytes())
    (target / 'SOURCES.json').write_text(json.dumps(used, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
