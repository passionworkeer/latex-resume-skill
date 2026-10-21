#!/usr/bin/env python3
"""Local Markdown resume editor with genuine LaTeX PDF previews."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
import signal
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import uuid
import webbrowser

SKILL = Path(__file__).resolve().parents[1]
MAX_SOURCE = 200_000
# JSON may expand a source byte to six bytes (for example, a control escape).
MAX_REQUEST = MAX_SOURCE * 6 + 2000
BUILD_TIMEOUT = 600
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
            self.draft.write_text(incoming, encoding='utf-8')
        elif not self.draft.exists():
            shutil.copyfile(SKILL / 'assets/templates/example-zh.md', self.draft)
        self.pages = pages
        self.python = python or sys.executable
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.builds = self.workspace / 'builds'
        self.builds.mkdir(exist_ok=True)

    def logos(self):
        path = SKILL / 'assets/logos/manifest.json'
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else data.get('logos', data.get('icons', []))

    def compile(self, source, pages, revision):
        # Save user edits before compilation, including drafts that have syntax errors.
        if self.draft.exists():
            shutil.copyfile(self.draft, self.workspace / 'resume.previous.md')
        temporary = self.workspace / 'resume.md.tmp'
        temporary.write_text(source, encoding='utf-8')
        temporary.replace(self.draft)
        build_id = uuid.uuid4().hex
        output = self.builds / build_id
        snapshots = self.workspace / 'snapshots'
        snapshots.mkdir(exist_ok=True)
        snapshot = snapshots / (build_id + '.md')
        snapshot.write_text(source, encoding='utf-8')
        command = [self.python, str(SKILL / 'scripts/build.py'), '--source', str(snapshot), '--output', str(output), '--pages', str(pages)]
        try:
            process = run_compile(command)
        except subprocess.TimeoutExpired:
            return {'ok': False, 'revision': revision, 'build_id': build_id, 'source_saved': True,
                    'error': '编译超过 600 秒，已停止本次编译进程，草稿已保存。首次生成可能需要几分钟下载排版资源；请先在终端完成 setup.py 和样例编译，再重试。'}
        report_file = output / 'verification.json'
        report = json.loads(report_file.read_text(encoding='utf-8')) if report_file.exists() else {}
        success = process.returncode == 0 and report.get('passed') is True
        previews = sorted(output.glob('preview-*.png'), key=lambda path: int(path.stem.split('-')[-1]))
        result = {'ok': success, 'revision': revision, 'build_id': build_id, 'source_saved': True,
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
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
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
                                 'source_name': 'resume.md', 'default_pages': self.state.pages, 'logos': self.state.logos()})
        elif path == '/api/draft':
            self.serve_file(self.state.draft, 'resume.md')
        elif path in {'/', '/index.html', '/editor/app.js', '/editor/styles.css'}:
            self.serve_file(SKILL / 'assets/editor' / ('index.html' if path == '/' else path.rsplit('/', 1)[-1]))
        elif path.startswith('/assets/logos/'):
            name = path.removeprefix('/assets/logos/')
            allowed = {item['file'] for item in self.state.logos()}
            if name not in allowed or Path(name).name != name:
                self.send_json(404, {'error': 'Unknown logo'})
                return
            self.serve_file(SKILL / 'assets/logos' / name)
        elif path.startswith('/builds/'):
            import re
            match = re.fullmatch(r'/builds/([a-f0-9]{32})/(resume\.pdf|preview-\d+\.png)', path)
            if not match:
                self.send_json(404, {'error': 'Not found'})
                return
            self.serve_file(self.state.builds / match[1] / match[2], 'resume.pdf' if match[2] == 'resume.pdf' else None)
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.trusted_request() or not hmac.compare_digest(self.headers.get('X-Session-Token', '').encode('utf-8'), self.state.token.encode('utf-8')):
            self.send_json(403, {'error': 'Invalid local editor session'})
            return
        if urlsplit(self.path).path != '/api/build':
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
            source, pages, revision = data['source'], data['pages'], data['revision']
            if not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > MAX_SOURCE:
                raise ValueError('Draft must contain 1–200000 UTF-8 bytes')
            if type(pages) is not int or not 1 <= pages <= 20:
                raise ValueError('Expected page count must be 1–20')
            if type(revision) is not int or revision < 0:
                raise ValueError('Invalid draft revision')
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            self.send_json(400, {'error': str(error)})
            return
        if not self.state.lock.acquire(blocking=False):
            self.send_json(409, {'error': 'A build is running; try again when it finishes'})
            return
        try:
            result = self.state.compile(source, pages, revision)
            self.send_json(200 if result['ok'] else 400, result)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            try:
                saved = self.state.draft.read_text(encoding='utf-8') == source
            except OSError:
                saved = False
            self.send_json(500, {'ok': False, 'revision': revision, 'source_saved': saved, 'error': str(error)})
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
