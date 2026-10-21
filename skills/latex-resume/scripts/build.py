#!/usr/bin/env python3
"""Compile the documented, deliberately small Markdown resume format."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def escape(text):
    mapping = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(mapping.get(c, c) for c in text)


def inline(text):
    """Return LaTeX and visible text; reject ambiguous Markdown constructs."""
    tex, plain = [], []
    i = 0
    while i < len(text):
        if text.startswith('![logo:', i):
            from logos import TOKEN, catalogue
            match = TOKEN.match(text, i)
            if not match or match[1] not in catalogue():
                raise ValueError('Unknown or malformed logo; see references/logos.md')
            tex.append(r'\resumeicon{' + match[1] + '}')
            i = match.end()
        elif text.startswith('**', i):
            end = text.find('**', i + 2)
            if end < 0 or end == i + 2:
                raise ValueError('Unclosed or empty bold span')
            value = text[i + 2:end]
            if any(c in value for c in '*[]`'):
                raise ValueError('Nested inline syntax is unsupported')
            tex.append(r'\textbf{' + escape(value) + '}')
            plain.append(value)
            i = end + 2
        elif text[i] == '[':
            match = re.match(r'\[([^\[\]\n]+)\]\((https?://[^\s()]+)\)', text[i:])
            if not match:
                raise ValueError('Links must use [label](https://...) without spaces or parentheses in URL')
            label, url = match.groups()
            if any(c in label for c in '*`') or any(c in url for c in '\\{}'):
                raise ValueError('Unsupported syntax in link')
            tex.append(r'\href{' + escape(url) + '}{' + escape(label) + '}')
            plain.append(label)
            i += match.end()
        else:
            c = text[i]
            if c in '*]`' or text.startswith('![', i) or c in '<>':
                raise ValueError('Unsupported Markdown syntax; use plain text, **bold**, or links')
            tex.append(escape(c))
            plain.append(c)
            i += 1
    return ''.join(tex), ''.join(plain)


def convert(source):
    body, expected = [], []
    in_list = False
    seen_name = False
    seen_section = False
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            if raw != raw.lstrip():
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
                body.append(r'\section{' + value + '}')
                seen_section = True
            elif line.startswith('### '):
                if not seen_section:
                    raise ValueError('Entry headings require a section')
                fields = line[4:].split('|')
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
        except ValueError as exc:
            raise ValueError(f'Line {number}: {exc}') from exc
    if not seen_name:
        raise ValueError('Start with # Name')
    if in_list:
        body.append(r'\end{itemize}')
    template = (ROOT / 'assets/templates/resume.tex').read_text(encoding='utf-8')
    return template.replace('%%BODY%%', '\n'.join(body)), '\n'.join(expected) + '\n'


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
    parser.add_argument('--bundle', default='https://data1b.fullyjustified.net/tlextras-2022.0r0.tar', help='Tectonic resource bundle URL or path')
    args = parser.parse_args()
    out = args.output.resolve()
    source_path = args.source.resolve()
    if out == ROOT or ROOT in out.parents or out == source_path.parent or source_path in [out / 'resume.tex', out / 'expected-text.txt', out / 'resume.pdf']:
        raise ValueError('Use a dedicated output directory outside the installed skill and source directory')
    if args.pages < 1:
        raise ValueError('--pages must be positive')
    out.mkdir(parents=True, exist_ok=True)
    clear_previous_results(out, source_path)
    tex, expected = convert(args.source.read_text(encoding='utf-8'))
    (out / 'resume.tex').write_text(tex, encoding='utf-8')
    (out / 'expected-text.txt').write_text(expected, encoding='utf-8')
    fonts = ROOT / 'assets/fonts'
    for name in ['NotoSansSC-Regular.ttf', 'NotoSansSC-Bold.ttf']:
        if not (fonts / name).is_file():
            raise RuntimeError('Missing fonts; run setup first: ' + str(fonts / name))
    shutil.copytree(fonts, out / 'fonts', dirs_exist_ok=True)
    shutil.copyfile(ROOT / 'assets/templates/LICENSE.txt', out / 'TEMPLATE-LICENSE.txt')
    from logos import TOKEN, prepare
    prepare(TOKEN.findall(args.source.read_text(encoding='utf-8')), out)
    engine, executable = select_engine(args.engine)
    if not executable:
        raise RuntimeError('No requested TeX engine available; run setup first')
    if engine == 'tectonic':
        command = [executable, '--untrusted', '--keep-logs', '--keep-intermediates', '--bundle', args.bundle, 'resume.tex']
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
