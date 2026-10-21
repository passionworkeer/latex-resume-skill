#!/usr/bin/env python3
"""Compile the documented, deliberately small Markdown resume format."""
import argparse
import os
import math
from pathlib import Path
import re
import shutil
import subprocess
import string
import sys

ROOT = Path(__file__).resolve().parents[1]
# Support both CLI execution and file-based imports used by embedders/tests.
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))


def escape(text):
    mapping = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(mapping.get(c, c) for c in text)


ESCAPABLE = frozenset(string.punctuation)
MAX_INLINE_DEPTH = 16


def dimension(value, minimum, maximum):
    if not re.fullmatch(r'\d+(?:\.\d+)?', value):
        raise ValueError('Invalid inline size')
    number = float(value)
    if not minimum <= number <= maximum or number * 2 != int(number * 2):
        raise ValueError(f'Inline size must be {minimum}–{maximum} in steps of 0.5')
    return f'{number:g}'


def split_entry(text):
    """Split only unescaped pipes; keep escapes for the inline parser."""
    fields, start, i = [], 0, 0
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text) and text[i + 1] in ESCAPABLE:
            i += 2
            continue
        if text[i] == '|':
            fields.append(text[start:i])
            start = i + 1
        i += 1
    return fields + [text[start:]]


def inline(text, _depth=0, _allow_links=True):
    """Parse the bounded inline grammar while retaining every visible character."""
    from logos import TOKEN, catalogue
    entries = None

    def parse(start=0, stop=None, depth=0, allow_links=True):
        nonlocal entries
        if depth > MAX_INLINE_DEPTH:
            raise ValueError('Inline nesting exceeds 16 levels')
        tex, plain, i = [], [], start
        while i < len(text):
            if stop and text.startswith(stop, i):
                if not tex:
                    raise ValueError('Empty inline span')
                return ''.join(tex), ''.join(plain), i + len(stop)
            if text[i] == '\\' and i + 1 < len(text) and text[i + 1] in ESCAPABLE:
                tex.append(escape(text[i + 1]))
                plain.append(text[i + 1])
                i += 2
            elif text.startswith('![logo:', i):
                match = TOKEN.match(text, i)
                if entries is None:
                    entries = catalogue()
                if not match or match[1] not in entries:
                    raise ValueError('Unknown or malformed logo; see references/logos.md')
                size = dimension(match[2], 8, 48) if match[2] else None
                tex.append(r'\resumeicon' + ('[' + size + ']' if size else '') + '{' + match[1] + '}')
                i = match.end()
            elif text.startswith('**', i):
                value, visible, i = parse(i + 2, '**', depth + 1, allow_links)
                tex.append(r'\textbf{' + value + '}')
                plain.append(visible)
            elif text.startswith('<size:', i):
                match = re.match(r'<size:([^<>]+)>', text[i:])
                if not match:
                    raise ValueError('Malformed size span')
                size = dimension(match[1], 8, 32)
                value, visible, i = parse(i + match.end(), '</size>', depth + 1, allow_links)
                tex.append(r'{\fontsize{' + size + '}{' + f'{float(size) * (13.8 / 10.5):.2f}'.rstrip('0').rstrip('.') + r'}\selectfont ' + value + '}')
                plain.append(visible)
            elif text[i] == '[' and allow_links:
                end = i + 1
                while end < len(text):
                    if text[end] == '\\' and end + 1 < len(text) and text[end + 1] in ESCAPABLE:
                        end += 2
                        continue
                    if text.startswith('](', end):
                        break
                    end += 1
                url_start = end + 2
                cursor, url = url_start, []
                while cursor < len(text) and text[cursor] != ')':
                    char = text[cursor]
                    if char == '\\' and cursor + 1 < len(text) and text[cursor + 1] in ESCAPABLE:
                        cursor += 1
                        char = text[cursor]
                    elif char == '(':
                        raise ValueError('URL parentheses must be escaped')
                    if char.isspace() or char in '{}\\':
                        raise ValueError('Unsupported URL character')
                    url.append(char)
                    cursor += 1
                url = ''.join(url)
                if cursor >= len(text) or not re.match(r'^(?:https?://|mailto:)[^\s]+$', url, re.I):
                    raise ValueError('Links must use HTTP(S) or mailto URLs')
                label = text[i + 1:end]
                if not label:
                    raise ValueError('Empty link label')
                label_tex, label_plain = inline(label, depth + 1, False)
                tex.append(r'\href{' + escape(url) + '}{' + label_tex + '}')
                plain.append(label_plain)
                i = cursor + 1
            else:
                c = text[i]
                if c in '*]`<>' or c == '[' or text.startswith('![', i):
                    raise ValueError('Unsupported or mismatched inline syntax')
                tex.append(escape(c))
                plain.append(c)
                i += 1
        if stop:
            raise ValueError('Unclosed inline span')
        return ''.join(tex), ''.join(plain), i

    tex, plain, _ = parse(depth=_depth, allow_links=_allow_links)
    return tex, plain


def validate_font_size(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 8 <= value <= 18 or value * 2 != int(value * 2):
        raise ValueError('Font size must be 8–18 in steps of 0.5')
    return float(value)


def convert(source, font_size=10.5, template_id='classic'):
    from templates import get_template, column_split
    selected_template = get_template(template_id)
    font_size = validate_font_size(font_size)
    body, expected = [], []
    section_starts, section_weights = [], []
    in_list = False
    seen_name = False
    seen_section = False
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            if raw != raw.lstrip() and re.match(r'^(?:#{1,6}\s|[-+*]\s|>\s|\d+[.)]\s|```|:::|\|)', line):
                raise ValueError('Indented or nested blocks are unsupported')
            if in_list and not line.startswith('- '):
                body.append(r'\end{itemize}')
                in_list = False
            if line.startswith('# '):
                if seen_name or body:
                    raise ValueError('Exactly one name heading must appear first')
                value, visible = inline(line[2:])
                body.append(r'\resumename{' + value + '}')
                seen_name = True
            elif not seen_name:
                raise ValueError('Start with # Name')
            elif line.startswith('## '):
                value, visible = inline(line[3:])
                section_starts.append(len(body))
                section_weights.append(0)
                body.append(r'\section{' + value + '}')
                seen_section = True
            elif line.startswith('### '):
                if not seen_section:
                    raise ValueError('Entry headings require a section')
                fields = split_entry(line[4:])
                if len(fields) != 3 or any(not f.strip() for f in fields):
                    raise ValueError('Entry heading must be ### Title | Role | Date')
                parsed = [inline(f.strip()) for f in fields]
                body.append(r'\entry{' + '}{'.join(p[0] for p in parsed) + '}')
                visible = ' '.join(p[1] for p in parsed)
            elif line.startswith('- '):
                if not seen_section:
                    raise ValueError('Bullets require a section')
                value, visible = inline(line[2:])
                if not in_list:
                    body.append(r'\begin{itemize}')
                    in_list = True
                body.append(r'\item ' + value)
            else:
                if re.match(r'^(#|[-+>]\s|\d+[.)]\s|:::|---|\|)', line):
                    raise ValueError('Unsupported block syntax')
                value, visible = inline(line)
                body.append((r'\contact{' + value + '}') if not seen_section else value + r'\par')
            if not visible.strip():
                raise ValueError('Empty content')
            expected.append(visible)
            if section_weights:
                section_weights[-1] += len(re.sub(r'\s', '', visible))
        except ValueError as exc:
            raise ValueError(f'Line {number}: {exc}') from exc
    if not seen_name:
        raise ValueError('Start with # Name')
    if in_list:
        body.append(r'\end{itemize}')
    template = (ROOT / 'assets/templates' / selected_template['filename']).read_text(encoding='utf-8')
    if template_id == 'two-column':
        first_section = next((i for i, line in enumerate(body) if line.startswith(r'\section{')), len(body))
        if first_section < len(body):
            split = column_split(section_weights)
            if split is not None:
                body.insert(section_starts[split], r'\columnbreak')
            body.insert(first_section, r'\begin{multicols}{2}')
            body.append(r'\end{multicols}')
    return template.replace('%%FONT_SIZE%%', f'{font_size:g}').replace('%%LINE_HEIGHT%%', f'{font_size * (13.8 / 10.5):.2f}'.rstrip('0').rstrip('.')).replace('%%BODY%%', '\n'.join(body)), '\n'.join(expected) + '\n'


def select_engine(choice):
    local = Path.cwd() / '.tools/bin' / ('tectonic.exe' if os.name == 'nt' else 'tectonic')
    tectonic = str(local) if local.is_file() else shutil.which('tectonic')
    xelatex = shutil.which('xelatex')
    if choice == 'auto':
        return ('tectonic', tectonic) if tectonic else ('xelatex', xelatex)
    return choice, tectonic if choice == 'tectonic' else xelatex


def clear_previous_results(out, source):
    """Invalidate only this builder's known outputs before any fallible work."""
    names = ['resume.pdf', 'resume.log', 'build.log', 'verification.json',
             'verification.extracted.txt', 'resume.tex', 'expected-text.txt',
             'resume.aux', 'resume.out', 'resume.xdv']
    paths = [out / name for name in names]
    paths.extend(p for p in out.glob('preview-*.png')
                 if re.fullmatch(r'preview-\d+\.png', p.name))
    if any(p.resolve() == source for p in paths):
        raise ValueError('Source must not be a generated output file')
    # Validate all candidates before mutating anything.
    if any(p.exists() and not p.is_file() for p in paths):
        raise ValueError('A generated output path is occupied by a directory')
    for path in paths:
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='Dedicated output directory')
    parser.add_argument('--engine', choices=['auto', 'tectonic', 'xelatex'], default='auto')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--font-size', type=float, default=10.5)
    from templates import catalogue
    parser.add_argument('--template', choices=[item['id'] for item in catalogue()], default='classic')
    parser.add_argument('--only-cached', action='store_true', help='Use only cached Tectonic resources')
    parser.add_argument('--bundle', default='https://data1b.fullyjustified.net/tlextras-2022.0r0.tar', help='Tectonic resource bundle URL or path')
    args = parser.parse_args()
    validate_font_size(args.font_size)
    out = args.output.resolve()
    source_path = args.source.resolve()
    if out == ROOT or ROOT in out.parents or out == source_path.parent or source_path in [out / 'resume.tex', out / 'expected-text.txt', out / 'resume.pdf']:
        raise ValueError('Use a dedicated output directory outside the installed skill and source directory')
    if args.pages < 1:
        raise ValueError('--pages must be positive')
    out.mkdir(parents=True, exist_ok=True)
    clear_previous_results(out, source_path)
    tex, expected = convert(args.source.read_text(encoding='utf-8'), args.font_size, args.template)
    (out / 'resume.tex').write_text(tex, encoding='utf-8')
    (out / 'expected-text.txt').write_text(expected, encoding='utf-8')
    fonts = ROOT / 'assets/fonts'
    for name in ['NotoSansSC-Regular.ttf', 'NotoSansSC-Bold.ttf']:
        if not (fonts / name).is_file():
            raise RuntimeError('Missing fonts; run setup first: ' + str(fonts / name))
    shutil.copytree(fonts, out / 'fonts', dirs_exist_ok=True)
    license_name = {'classic': 'LICENSE.txt', 'minimal': 'LICENSE.sb2nov.txt', 'two-column': 'LICENSE.latexcv.txt'}[args.template]
    license_paths = ['LICENSE.txt'] if args.template == 'classic' else ['LICENSE.txt', license_name]
    (out / 'TEMPLATE-LICENSE.txt').write_text('\n\n'.join((ROOT / 'assets/templates' / name).read_text(encoding='utf-8') for name in license_paths), encoding='utf-8')
    from logos import prepare
    prepare(re.findall(r'\\resumeicon(?:\[[0-9.]+\])?\{([a-z0-9-]+)\}', tex), out)
    engine, executable = select_engine(args.engine)
    if not executable:
        raise RuntimeError('No requested TeX engine available; run setup first')
    if engine == 'tectonic':
        command = [executable, '--untrusted', '--keep-logs', '--keep-intermediates', '--bundle', args.bundle, 'resume.tex']
        if args.only_cached:
            command.insert(1, '-C')
    else:
        command = [executable, '-no-shell-escape', '-halt-on-error', '-file-line-error', '-interaction=nonstopmode', 'resume.tex']
    result = subprocess.run(command, cwd=out, capture_output=True, text=True)
    (out / 'build.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode or not (out / 'resume.pdf').is_file():
        raise RuntimeError('Compilation failed; inspect ' + str(out / 'build.log'))
    verify = subprocess.run([sys.executable, str(ROOT / 'scripts/verify.py'), '--pdf', str(out / 'resume.pdf'), '--expected', str(out / 'expected-text.txt'), '--pages', str(args.pages), '--log', str(out / 'resume.log'), '--report', str(out / 'verification.json'), '--render', str(out / 'preview')])
    raise SystemExit(verify.returncode)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
