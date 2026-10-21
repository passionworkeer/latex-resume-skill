#!/usr/bin/env python3
"""Explicitly download pinned school artwork for private local use, never redistribution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

import logos

PRESENTATION = {'fill', 'fill-rule', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-linecap',
                'stroke-linejoin', 'stroke-opacity', 'stroke-miterlimit', 'opacity', 'clip-rule'}


def normalize_svg(raw):
    """Expand plain inline presentation declarations; retain every drawing/coordinate/color.

    Unsupported elements, DTDs, links, CSS rules, URLs and active content still fail the
    existing SVG gate. This is not an arbitrary SVG sanitizer or a renderer fallback.
    """
    try:
        logos.validate_svg(raw)
        return raw
    except ValueError:
        pass
    if len(raw) > 500_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('SVG is too large or contains a DTD/entity')
    root = ET.fromstring(raw)
    for element in root.iter():
        style = element.attrib.pop('style', None)
        if style is not None:
            for declaration in style.split(';'):
                if not declaration.strip():
                    continue
                key, separator, value = declaration.partition(':')
                key, value = key.strip(), value.strip()
                if not separator or key not in PRESENTATION or not value or re.search(r'url\s*\(|javascript:|https?:|file:|data:|@|[{}]', value, re.I):
                    raise ValueError('Unsupported inline SVG presentation style')
                element.set(key, value)
    result = ET.tostring(root, encoding='utf-8')
    logos.validate_svg(result)
    return result


def fetch(school):
    destination = logos.DIRECTORY / 'local'
    destination.mkdir(exist_ok=True)
    if destination.is_symlink():
        raise ValueError('Local logo directory cannot be a symlink')
    request = urllib.request.Request(school['source_svg_url'], headers={'User-Agent': 'latex-resume-school-assets/1'})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read(500_001)
    if hashlib.sha256(raw).hexdigest() != school['source_svg_sha256']:
        raise ValueError('Pinned source checksum mismatch')
    safe = normalize_svg(raw)
    entry = dict(id=school['id'], name=school['name'], english_name=school['english_name'],
                 aliases=school['aliases'], file=school['id']+'.svg', category='school', local=True,
                 source=school['source_svg_url'], source_sha256=school['source_svg_sha256'],
                 sha256=hashlib.sha256(safe).hexdigest(), source_commit=school['source_repository_commit'],
                 license=school['license_status'], individual_license=None,
                 brand_url=school['official_url'], guidelines_url=school['official_url'],
                 rights_notice='Local download only; no redistribution grant is represented. Follow institution identity rules; no endorsement implied.',
                 transformation='none' if safe == raw else 'Inline presentation style declarations expanded to equivalent SVG attributes; geometry and colors unchanged.')
    path = destination / entry['file']
    if path.is_symlink():
        raise ValueError('Local logo file cannot be a symlink')
    path.write_bytes(safe)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--school', help='School abbreviation, e.g. bupt')
    choice.add_argument('--all', action='store_true', help='Try all pinned candidates; unsupported SVGs remain absent')
    args = parser.parse_args()
    schools = json.loads((logos.DIRECTORY/'manifest.json').read_text(encoding='utf-8'))['university_sources']['entries']
    selected = schools if args.all else [s for s in schools if s['id'] == args.school.lower()]
    if not selected:
        parser.error('Unknown school; see university_sources in assets/logos/manifest.json')
    manifest = logos.DIRECTORY/'local/manifest.json'
    if manifest.is_symlink() or manifest.parent.is_symlink():
        raise ValueError('Local logo manifest/directory cannot be a symlink')
    existing = json.loads(manifest.read_text(encoding='utf-8'))['icons'] if manifest.exists() else []
    entries = {e['id']: e for e in existing}
    failures = []
    successes = 0
    for school in selected:
        try:
            entry = fetch(school)
            entries[entry['id']] = entry
            successes += 1
            print('Downloaded locally:', entry['id'])
        except (ValueError, OSError, ET.ParseError) as error:
            failures.append(school['id'])
            print('Unavailable:', school['id'], '-', error)
    if entries:
        temporary = manifest.with_suffix('.json.tmp')
        if temporary.is_symlink():
            raise ValueError('Local logo temporary manifest cannot be a symlink')
        temporary.write_text(json.dumps({'schema_version': 1, 'rights_notice': 'Private local downloads, excluded from Git. Institution artwork rights remain with their owners.', 'icons': list(entries.values())}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temporary.replace(manifest)
    print(f'{len(entries)} local schools available; {len(failures)} downloads rejected or failed.')
    return 1 if successes == 0 or (failures and not args.all) else 0


if __name__ == '__main__':
    raise SystemExit(main())
