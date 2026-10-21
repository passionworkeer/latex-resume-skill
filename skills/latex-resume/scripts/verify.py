#!/usr/bin/env python3
"""Verify text, page count, visible glyph bounds and TeX diagnostics; render previews."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def normalize(text):
    return re.sub(r'[\s•‧∙●]', '', text)


def compare(expected, actual):
    a, b = normalize(expected), normalize(actual)
    return {'exact_text_match': a == b, 'expected_characters': len(a), 'actual_characters': len(b),
            'differences': [{'kind': t, 'expected': a[i:j], 'actual': b[k:l]} for t, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if t != 'equal']}


def check(pdf_path, expected, pages=1, log_path=None):
    import pdfplumber
    actual, bounds, sizes = [], [], []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            # Content order preserves the title/role/date order of generated rows.
            actual.extend(c['text'] for c in page.chars)
            sizes.append({'page': index, 'width_pt': page.width, 'height_pt': page.height})
            for char in page.chars:
                if not char['text'].strip():
                    continue
                if char['x0'] < -0.5 or char['x1'] > page.width + 0.5 or char['top'] < -0.5 or char['bottom'] > page.height + 0.5:
                    bounds.append({'page': index, 'text': char['text'], 'box': [char['x0'], char['top'], char['x1'], char['bottom']]})
        count = len(pdf.pages)
    if log_path is not None and (not log_path.is_file() or not log_path.stat().st_size):
        raise ValueError('Requested compilation log is missing or empty: ' + str(log_path))
    log = log_path.read_text(encoding='utf-8', errors='replace') if log_path else ''
    warnings = [line for line in log.splitlines() if re.search(r'Missing character|Font Warning|font.*(?:not found|substitut)|Overfull \\[hv]box', line, re.I)]
    report = compare(expected, ''.join(actual))
    report.update({'pdf_sha256': hashlib.sha256(pdf_path.read_bytes()).hexdigest(), 'expected_text_sha256': hashlib.sha256(expected.encode('utf-8')).hexdigest(), 'log_sha256': hashlib.sha256(log.encode('utf-8')).hexdigest() if log else None, 'page_count': count, 'expected_pages': pages, 'page_sizes': sizes, 'out_of_page_glyphs': bounds, 'font_and_overflow_warnings': warnings, 'log_checked': bool(log), 'visual_check_required': True, 'visual_status': 'PENDING: inspect every rendered page before delivery'})
    report['passed'] = report['exact_text_match'] and count == pages and not bounds and not warnings and bool(log)
    return report, ''.join(actual)


def render(pdf, prefix):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for stale in prefix.parent.glob(prefix.name + '-*.png'):
        stale.unlink()
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm', '-png', '-r', '120', str(pdf), str(prefix)], check=True, capture_output=True)
    else:
        import fitz
        with fitz.open(pdf) as document:
            for i, page in enumerate(document, 1):
                page.get_pixmap(matrix=fitz.Matrix(120 / 72, 120 / 72)).save(str(prefix) + f'-{i}.png')
    return sorted(str(p) for p in prefix.parent.glob(prefix.name + '-*.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--expected', type=Path, help='Independent visible-text ledger')
    group.add_argument('--source', type=Path, help='Supported Markdown source')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--render', type=Path, help='PNG output prefix')
    args = parser.parse_args()
    if args.pages < 1:
        parser.error('--pages must be positive')
    if args.source:
        from build import convert
        _, expected = convert(args.source.read_text(encoding='utf-8'))
    else:
        expected = args.expected.read_text(encoding='utf-8')
    report, actual = check(args.pdf, expected, args.pages, args.log)
    if args.render:
        report['previews'] = render(args.pdf, args.render)
    target = args.report or args.pdf.with_suffix('.verification.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    target.with_suffix('.extracted.txt').write_text(actual, encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
