#!/usr/bin/env python3
"""Local Markdown resume editor with genuine LaTeX PDF previews."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import io
import zipfile
import mimetypes
import math
import os
import signal
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit, parse_qs
import uuid
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from templates import catalogue, get_template
import logos as logo_assets

SKILL = Path(__file__).resolve().parents[1]
MAX_SOURCE = 200_000
# JSON may expand a source byte to six bytes (for example, a control escape).
MAX_REQUEST = MAX_SOURCE * 6 + 2000
BUILD_TIMEOUT = 600


def validate_template_id(value):
    if not isinstance(value, str):
        raise ValueError('Invalid template ID')
    get_template(value)
    return value


def validate_font_size(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 9 <= value <= 12 or value * 2 != int(value * 2):
        raise ValueError('Font size must be 9–12 in steps of 0.5')
    return float(value)


def validate_pages(value):
    if type(value) is not int or not 1 <= value <= 20:
        raise ValueError('Expected page count must be 1–20')
    return value

IS_WINDOWS = os.name == 'nt'


def run_compile(command, timeout=BUILD_TIMEOUT):
    """Bound the entire compiler process tree, including TeX grandchildren."""
    environment = os.environ.copy()
    environment['PYTHONIOENCODING'] = 'utf-8'
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               encoding='utf-8', errors='replace', env=environment,
                               start_new_session=not IS_WINDOWS)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # build.py starts its own TeX and verification children. Killing only
        # build.py leaves those running and can hold inherited stdout pipes open.
        if IS_WINDOWS:
            # taskkill /T includes the compiler children on Windows.
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, check=False)
            if process.poll() is None:
                process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class EditorState:
    def __init__(self, workspace, source=None, pages=1, python=None):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.draft = self.workspace / 'resume.md'
        if source:
            incoming = Path(source).read_text(encoding='utf-8')
            if self.draft.exists() and self.draft.read_text(encoding='utf-8') != incoming:
                raise ValueError('Workspace already has a different draft. Omit --source to resume it, or choose a new --workspace.')
            self.draft.write_bytes(incoming.encode('utf-8'))
        elif not self.draft.exists():
            shutil.copyfile(SKILL / 'assets/templates/example-zh.md', self.draft)
        self.settings_file = self.workspace / 'editor-settings.json'
        self.pages, self.font_size, self.template_id = pages, 10.5, 'classic'
        if self.settings_file.exists():
            settings = json.loads(self.settings_file.read_text(encoding='utf-8'))
            self.pages = validate_pages(settings['pages'])
            self.font_size = validate_font_size(settings['font_size'])
            self.template_id = validate_template_id(settings.get('template_id', 'classic'))
        self.python = python or sys.executable
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.builds = self.workspace / 'builds'
        self.builds.mkdir(exist_ok=True)

    def logos(self):
        return list(logo_assets.catalogue().values())

    def save(self, source, revision, pages=None, font_size=None, template_id=None):
        """Atomically save a draft; the caller holds the shared save/build lock."""
        settings = {'pages': self.pages if pages is None else validate_pages(pages),
                    'font_size': self.font_size if font_size is None else validate_font_size(font_size),
                    'template_id': validate_template_id(self.template_id if template_id is None else template_id)}
        if self.draft.exists():
            shutil.copyfile(self.draft, self.workspace / 'resume.previous.md')
        temporary = self.workspace / 'resume.md.tmp'
        temporary.write_bytes(source.encode('utf-8'))
        temporary.replace(self.draft)
        settings_tmp = self.settings_file.with_suffix('.json.tmp')
        settings_tmp.write_text(json.dumps(settings), encoding='utf-8')
        settings_tmp.replace(self.settings_file)
        self.pages, self.font_size, self.template_id = settings['pages'], settings['font_size'], settings['template_id']
        return {'ok': True, 'source_saved': True, 'revision': revision}

    def compile(self, source, pages, revision, font_size=10.5, template_id='classic'):
        # Save user edits before compilation, including drafts that have syntax errors.
        self.save(source, revision, pages, font_size, template_id)
        build_id = uuid.uuid4().hex
        output = self.builds / build_id
        snapshots = self.workspace / 'snapshots'
        snapshots.mkdir(exist_ok=True)
        snapshot = snapshots / (build_id + '.md')
        snapshot.write_bytes(source.encode('utf-8'))
        command = [self.python, str(SKILL / 'scripts/build.py'), '--source', str(snapshot), '--output', str(output), '--pages', str(pages), '--font-size', str(font_size), '--template', template_id]
        try:
            process = run_compile(command + ['--only-cached'])
            if process.returncode:
                log = output / 'build.log'
                diagnostics = process.stdout + process.stderr + (log.read_text(encoding='utf-8', errors='replace') if log.exists() else '')
                missing_cache = any(marker in diagnostics.lower() for marker in (
                    "isn't cached", 'not cached', 'not found in cache',
                    'not available in cache', "couldn't open", 'could not find',
                    'failed to open', 'failed to load the format'))
                if missing_cache:
                    process = run_compile(command)
        except subprocess.TimeoutExpired:
            return {'ok': False, 'revision': revision, 'build_id': build_id, 'source_saved': True, 'template_id': template_id,
                    'error': '编译超过 600 秒，已停止本次编译进程，草稿已保存。首次生成可能需要几分钟下载排版资源；请先在终端完成 setup.py 和样例编译，再重试。'}
        report_file = output / 'verification.json'
        report = json.loads(report_file.read_text(encoding='utf-8')) if report_file.exists() else {}
        success = process.returncode == 0 and report.get('passed') is True
        previews = sorted(output.glob('preview-*.png'), key=lambda path: int(path.stem.split('-')[-1]))
        result = {'ok': success, 'revision': revision, 'build_id': build_id, 'source_saved': True, 'template_id': template_id,
                  'report': report, 'previews': [f'/builds/{build_id}/{p.name}' for p in previews],
                  'pdf_url': f'/builds/{build_id}/resume.pdf' if success else None}
        # Absolute local paths are not needed by the viewer.
        result['report'].pop('previews', None)
        if not success:
            logfile = output / 'build.log'
            result['error'] = '生成或验证未通过；草稿已保存。请按下方信息修改后重试。'
            result['log'] = (process.stdout + process.stderr + ('\n' + logfile.read_text(encoding='utf-8', errors='replace') if logfile.exists() else ''))[-16000:]
        return result


class EditorHandler(BaseHTTPRequestHandler):
    server_version = 'ResumeEditor/1.0'

    @property
    def state(self):
        return self.server.editor_state

    def log_message(self, fmt, *args):
        # Do not print user content, tokens, or request URLs into terminal history.
        if args and isinstance(args[0], str) and args[0].startswith(('GET ', 'POST ')):
            return
        super().log_message(fmt, *args)

    def trusted_request(self):
        port = self.server.server_address[1]
        host = self.headers.get('Host', '')
        if host not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
            return False
        origin = self.headers.get('Origin')
        return not origin or origin == 'http://' + host

    def send_bytes(self, status, data, content_type, attachment=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        # ByteMD injects editor styles; image export clones those styles inline.
        # Scripts remain external and same-origin, with no eval permission.
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if attachment:
            self.send_header('Content-Disposition', f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, obj):
        self.send_bytes(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def serve_file(self, file, attachment=None):
        if not file.is_file():
            self.send_json(404, {'error': 'Not found'})
            return
        mime = {'.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8'}.get(file.suffix, mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        self.send_bytes(200, file.read_bytes(), mime, attachment)

    def do_GET(self):
        if not self.trusted_request():
            self.send_json(403, {'error': 'Only this local editor origin is allowed'})
            return
        path = urlsplit(self.path).path
        if path == '/api/session':
            self.send_json(200, {'token': self.state.token, 'source': self.state.draft.read_text(encoding='utf-8'),
                                 'source_name': 'resume.md', 'default_pages': self.state.pages, 'font_size': self.state.font_size, 'logos': self.state.logos(), 'templates': catalogue(), 'template_id': self.state.template_id})
        elif path == '/api/draft':
            self.serve_file(self.state.draft, 'resume.md')
        elif path in {'/', '/index.html', '/editor/styles.css', '/editor/bundle.js', '/editor/bundle.css', '/editor/resume.css'}:
            self.serve_file(SKILL / 'assets/editor' / ('index.html' if path == '/' else path.rsplit('/', 1)[-1]))
        elif path in {'/assets/fonts/NotoSansSC-Regular.ttf', '/assets/fonts/NotoSansSC-Bold.ttf'}:
            self.serve_file(SKILL / 'assets/fonts' / path.rsplit('/', 1)[-1])
        elif path.startswith('/assets/templates/thumbnails/'):
            allowed = {f'/assets/templates/thumbnails/{item["id"]}.png' for item in catalogue()}
            if path not in allowed:
                self.send_json(404, {'error': 'Unknown template thumbnail'})
                return
            self.serve_file(SKILL / 'assets/templates/thumbnails' / path.rsplit('/', 1)[-1])
        elif path.startswith('/assets/logos/'):
            name = path.removeprefix('/assets/logos/')
            allowed = {item['file'] for item in self.state.logos()}
            if name not in allowed or Path(name).name != name:
                self.send_json(404, {'error': 'Unknown logo'})
                return
            try:
                logo_path = logo_assets.resolve_logo_path(name)
            except (ValueError, OSError):
                self.send_json(404, {'error': 'Unknown logo'})
                return
            self.serve_file(logo_path)
        elif path.startswith('/builds/'):
            import re
            match = re.fullmatch(r'/builds/([a-f0-9]{32})/(resume\.pdf|preview-\d+\.png|previews\.zip)', path)
            if not match:
                self.send_json(404, {'error': 'Not found'})
                return
            if match[2] == 'previews.zip':
                directory = self.state.builds / match[1]
                previews = sorted((p for p in directory.glob('preview-*.png') if re.fullmatch(r'preview-\d+\.png', p.name) and p.is_file()),
                                  key=lambda p: int(p.stem.split('-')[-1]))
                if not previews:
                    self.send_json(404, {'error': 'Not found'})
                    return
                archive = io.BytesIO()
                with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
                    for preview in previews:
                        package.write(preview, preview.name)
                self.send_bytes(200, archive.getvalue(), 'application/zip', 'resume-previews.zip')
                return
            attachment = match[2] if match[2] == 'resume.pdf' or parse_qs(urlsplit(self.path).query).get('download') == ['1'] else None
            self.serve_file(self.state.builds / match[1] / match[2], attachment)
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.trusted_request() or not hmac.compare_digest(self.headers.get('X-Session-Token', '').encode('utf-8'), self.state.token.encode('utf-8')):
            self.send_json(403, {'error': 'Invalid local editor session'})
            return
        endpoint = urlsplit(self.path).path
        if endpoint not in {'/api/build', '/api/save'}:
            self.send_json(404, {'error': 'Not found'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.send_json(415, {'error': 'Expected JSON'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > MAX_REQUEST:
                raise ValueError('Request is too large or empty')
            data = json.loads(self.rfile.read(length))
            source, revision = data['source'], data['revision']
            template_id = validate_template_id(data['template_id']) if 'template_id' in data else None
            pages = validate_pages(data['pages']) if 'pages' in data else None
            font_size = validate_font_size(data['font_size']) if 'font_size' in data else None
            if not isinstance(source, str) or len(source.encode('utf-8')) > MAX_SOURCE:
                raise ValueError('Draft must contain at most 200000 UTF-8 bytes')
            if endpoint == '/api/build':
                if not source.strip():
                    raise ValueError('Draft must contain 1–200000 UTF-8 bytes')
                pages = validate_pages(data['pages'])
                font_size = 10.5 if font_size is None else font_size
            if type(revision) is not int or revision < 0:
                raise ValueError('Invalid draft revision')
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            self.send_json(400, {'error': str(error)})
            return
        if not self.state.lock.acquire(blocking=False):
            self.send_json(409, {'error': 'A save or build is running; try again when it finishes'})
            return
        try:
            template_id = self.state.template_id if template_id is None else template_id
            result = self.state.save(source, revision, pages, font_size, template_id) if endpoint == '/api/save' else self.state.compile(source, pages, revision, font_size, template_id)
            self.send_json(200 if result['ok'] else 400, result)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            try:
                saved = self.state.draft.read_text(encoding='utf-8') == source
            except OSError:
                saved = False
            self.send_json(500, {'ok': False, 'revision': revision, 'source_saved': saved, 'template_id': template_id, 'error': str(error)})
        finally:
            self.state.lock.release()


def make_server(state, port=0):
    server = ThreadingHTTPServer(('127.0.0.1', port), EditorHandler)
    server.editor_state = state
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd() / 'private/editor')
    parser.add_argument('--source', type=Path, help='Import a Markdown file into a new workspace')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--port', type=int, default=8765, help='Local port; use 0 to choose an available port')
    parser.add_argument('--no-open', action='store_true', help='Do not open the system default browser')
    args = parser.parse_args()
    if not 1 <= args.pages <= 20:
        parser.error('--pages must be 1–20')
    state = EditorState(args.workspace, args.source, args.pages)
    server = make_server(state, args.port)
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print('Resume editor:', url, flush=True)
    print('Saved draft:', state.draft, flush=True)
    print('Press Ctrl+C to stop. Only the local computer can connect.', flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
