#!/usr/bin/env python3
"""Install the resume toolchain into the current workspace; no sudo or shell scripts."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

SKILL = Path(__file__).resolve().parents[1]
LOCK = json.loads((SKILL / 'scripts/downloads.json').read_text())


def run(args):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def download(info, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == info['sha256']:
        return dest
    print('Downloading', info['url'], flush=True)
    req = urllib.request.Request(info['url'], headers={'User-Agent': 'latex-resume-skill'})
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != info['sha256']:
        raise RuntimeError('Download checksum mismatch: ' + dest.name)
    tmp = dest.with_suffix(dest.suffix + '.part')
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def engine(workspace):
    filename = 'tectonic.exe' if os.name == 'nt' else 'tectonic'
    local = workspace / '.tools/bin' / filename
    return str(local) if local.is_file() else shutil.which('tectonic') or shutil.which('xelatex')


def ensure_engine(workspace):
    if engine(workspace):
        return
    machine = platform.machine().lower()
    arch = {'arm64': 'aarch64', 'amd64': 'x86_64'}.get(machine, machine)
    key = platform.system().lower() + '-' + arch
    info = LOCK['tectonic'].get(key)
    if not info:
        raise RuntimeError('No portable engine for ' + key + '. Install Tectonic or XeLaTeX using your platform package manager, then rerun setup.')
    archive = download(info, workspace / '.cache' / info['filename'])
    target = workspace / '.tools/bin' / ('tectonic.exe' if os.name == 'nt' else 'tectonic')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Extract only the executable bytes, never archive paths or symlinks.
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as z:
            matches = [x for x in z.namelist() if Path(x).name == target.name]
            if len(matches) != 1:
                raise RuntimeError('Unexpected engine archive structure')
            data = z.read(matches[0])
    else:
        with tarfile.open(archive, 'r:gz') as t:
            matches = [x for x in t.getmembers() if x.isfile() and Path(x.name).name == target.name]
            if len(matches) != 1:
                raise RuntimeError('Unexpected engine archive structure')
            data = t.extractfile(matches[0]).read()
    target.write_bytes(data)
    target.chmod(0o755)
    run([target, '--version'])


def preserve_text_cmap(font):
    """Give punctuation aliases distinct glyph IDs so PDF ToUnicode is lossless."""
    codepoints = [0x2D, 0xAD, 0x2011, 0xB7, 0x2022, 0x2027, 0x30FB]
    cmap = font.getBestCmap()
    for cp in codepoints:
        original = cmap.get(cp)
        if original is None:
            continue
        name = f'resume_uni{cp:04X}'
        if name not in font.getGlyphOrder():
            order = list(font.getGlyphOrder())
            font['glyf'][name] = copy.deepcopy(font['glyf'][original])
            for metric in ['hmtx', 'vmtx']:
                if metric in font:
                    font[metric].metrics[name] = font[metric].metrics[original]
            font.setGlyphOrder(order + [name])
        for table in font['cmap'].tables:
            if table.isUnicode() and cp in table.cmap:
                table.cmap[cp] = name


def ensure_fonts(workspace):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    font_dir = SKILL / 'assets/fonts'
    font_dir.mkdir(parents=True, exist_ok=True)
    license_file = download(LOCK['fonts']['OFL.txt'], workspace / '.cache/OFL.txt')
    shutil.copyfile(license_file, font_dir / 'OFL.txt')
    variable = download(LOCK['fonts']['NotoSansSC-Variable.ttf'], workspace / '.cache/NotoSansSC-Variable.ttf')
    stamp = font_dir / 'build.json'
    desired = {'source_sha256': LOCK['fonts']['NotoSansSC-Variable.ttf']['sha256'], 'recipe': 2}
    if stamp.exists():
        previous = json.loads(stamp.read_text())
        if all(previous.get(k) == v for k, v in desired.items()) and all(
            (font_dir / n).is_file() and hashlib.sha256((font_dir / n).read_bytes()).hexdigest() == h
            for n, h in previous.get('files', {}).items()
        ) and len(previous.get('files', {})) == 2:
            return
    hashes = {}
    with TTFont(variable) as source:
        for weight, style in [(400, 'Regular'), (700, 'Bold')]:
            print('Preparing font:', style, flush=True)
            font = instantiateVariableFont(source, {'wght': weight}, inplace=False)
            preserve_text_cmap(font)
            name = 'NotoSansSC-' + style + '.ttf'
            font.save(font_dir / name)
            font.close()
            hashes[name] = hashlib.sha256((font_dir / name).read_bytes()).hexdigest()
    stamp.write_text(json.dumps({**desired, 'files': hashes}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--check', action='store_true', help='Read-only dependency diagnosis')
    parser.add_argument('--fonts-only', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    python = workspace / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if args.check:
        missing = []
        if not python.is_file():
            missing.append('workspace .venv')
        else:
            result = subprocess.run([str(python), '-c', 'import pdfplumber, pymupdf, fontTools'], capture_output=True)
            if result.returncode:
                missing.append('Python packages')
        found = engine(workspace)
        if not found:
            missing.append('Tectonic or XeLaTeX')
        for name in ['Regular', 'Bold']:
            if not (SKILL / 'assets/fonts' / ('NotoSansSC-' + name + '.ttf')).is_file():
                missing.append('Noto Sans SC ' + name)
        print(json.dumps({'ready': not missing, 'missing': missing, 'engine': found}, indent=2))
        return int(bool(missing))
    if args.fonts_only:
        ensure_fonts(workspace)
        return 0
    workspace.mkdir(parents=True, exist_ok=True)
    if not python.is_file():
        print('Creating isolated Python environment', flush=True)
        # Resolve shim/symlink launchers so venv records the real standard-library home.
        run([Path(sys.executable).resolve(), '-m', 'venv', workspace / '.venv'])
    run([python, '-m', 'pip', 'install', '-r', SKILL / 'requirements.txt'])
    ensure_engine(workspace)
    run([python, Path(__file__), '--workspace', workspace, '--fonts-only'])
    print('Ready. Use', python, 'to run scripts/build.py. First compilation downloads TeX packages.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('Setup failed:', error, file=sys.stderr)
        print('Check network/proxy, Python venv support, and platform availability; fix the reported dependency and rerun. Completed downloads are cached.', file=sys.stderr)
        sys.exit(1)
