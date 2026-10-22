#!/usr/bin/env python3
"""Register or import a user-supplied custom SVG logo into the local catalogue."""
import argparse
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))

from logos import validate_svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, type=Path, help='Path to custom SVG logo file')
    parser.add_argument('--id', type=str, default=None, help='Unique slug for the logo (lowercase alphanumeric and hyphens)')
    parser.add_argument('--name', type=str, default=None, help='Display name for the logo')
    args = parser.parse_args()

    svg_path = args.file.resolve()
    if not svg_path.is_file():
        raise ValueError(f'File not found: {svg_path}')
    raw = svg_path.read_bytes()
    validate_svg(raw)

    slug = args.id or svg_path.stem.lower()
    slug = re.sub(r'[^a-z0-9-]', '-', slug).strip('-')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', slug):
        raise ValueError('Logo ID must be 1–64 characters of lowercase alphanumeric and hyphens')

    dest_dir = ROOT / 'assets/logos/custom'
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f'{slug}.svg'
    shutil.copyfile(svg_path, dest_file)
    print(f'Successfully installed custom logo: {slug} -> {dest_file}')
    print(f'You can now use ![logo:{slug}] in your resume Markdown.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
