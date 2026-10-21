"""Local editor HTTP and draft lifecycle regression tests (no TeX/browser)."""
import http.client
import importlib.util
import json
import io
import zipfile
import os
import signal
import sys
import time
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/latex-resume/scripts/preview.py'
spec = importlib.util.spec_from_file_location('resume_preview', SCRIPT)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / 'editor'
        self.state = preview.EditorState(self.workspace)
        self.server = preview.make_server(self.state)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method='GET', path='/api/session', data=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        request_headers = {'Host': f'127.0.0.1:{self.port}'}
        body = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode()
            request_headers.update({'Content-Type': 'application/json', 'X-Session-Token': self.state.token})
        request_headers.update(headers or {})
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def build(self, **overrides):
        data = {'source': '# 测试\n## 经历\n- 新内容', 'pages': 1, 'revision': 7}
        data.update(overrides)
        return self.request('POST', '/api/build', data)

    def test_session_and_download_draft(self):
        status, headers, body = self.request()
        session = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(session['token'], self.state.token)
        self.assertEqual(session['source'], self.state.draft.read_text(encoding='utf-8'))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        status, headers, body = self.request(path='/api/draft')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(body, self.state.draft.read_bytes())

    def test_foreign_host_origin_and_invalid_token_are_denied(self):
        for headers in [{'Host': 'attacker.example'}, {'Origin': 'https://attacker.example'}, {'Origin': 'null'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request(headers=headers)[0], 403)
        for headers in [{'X-Session-Token': ''}, {'X-Session-Token': 'wrong'}, {'X-Session-Token': 'é'}, {'Origin': 'https://attacker.example'}, {'Host': 'attacker.example'}]:
            with self.subTest(headers=headers), patch.object(self.state, 'compile') as compile_mock:
                self.assertEqual(self.request('POST', '/api/build', {'source': '# x', 'pages': 1, 'revision': 0}, headers)[0], 403)
                compile_mock.assert_not_called()

    def test_invalid_payload_never_writes_draft(self):
        original = self.state.draft.read_bytes()
        for values in [{'source': ''}, {'source': None}, {'source': '汉' * 70000}, {'pages': True}, {'pages': 0}, {'pages': 21}, {'revision': -1}, {'revision': True}]:
            with self.subTest(fields=list(values)), patch.object(self.state, 'compile') as compile_mock:
                self.assertEqual(self.build(**values)[0], 400)
                compile_mock.assert_not_called()
                self.assertEqual(self.state.draft.read_bytes(), original)
        self.assertFalse((self.workspace / 'resume.previous.md').exists())

    def test_save_utf8_draft_and_backup_without_compilation(self):
        previous = self.state.draft.read_bytes()
        source = '# 林知遥\n\n实时预览 · résumé 🚀'
        with patch.object(self.state, 'compile') as compile_mock:
            status, _, body = self.request('POST', '/api/save', {'source': source, 'revision': 12})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'ok': True, 'source_saved': True, 'revision': 12})
        compile_mock.assert_not_called()
        self.assertEqual(self.state.draft.read_bytes(), source.encode('utf-8'))
        self.assertEqual((self.workspace / 'resume.previous.md').read_bytes(), previous)
        self.assertEqual(json.loads(self.request()[2])['source'], source)
        self.assertEqual(self.request(path='/api/draft')[2], source.encode('utf-8'))
        self.assertFalse((self.workspace / 'resume.md.tmp').exists())

    def test_save_allows_empty_and_whitespace_drafts(self):
        for revision, source in enumerate(['', ' \n\t']):
            with self.subTest(source=source):
                status, _, body = self.request('POST', '/api/save', {'source': source, 'revision': revision})
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(body)['source_saved'])
                self.assertEqual(self.state.draft.read_text(encoding='utf-8'), source)
                self.assertEqual(self.build(source=source)[0], 400)

    def test_save_rejects_invalid_session_and_payload_without_writing(self):
        original = self.state.draft.read_bytes()
        for headers in [{'X-Session-Token': 'wrong'}, {'Origin': 'https://attacker.example'}, {'Host': 'attacker.example'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request('POST', '/api/save', {'source': '# changed', 'revision': 0}, headers)[0], 403)
        for data in [{'source': None, 'revision': 0}, {'source': '汉' * 70000, 'revision': 0}, {'source': '# x', 'revision': True}, {'source': '# x', 'revision': -1}, {'source': '# x'}]:
            with self.subTest(fields=list(data)):
                self.assertEqual(self.request('POST', '/api/save', data)[0], 400)
        self.assertEqual(self.state.draft.read_bytes(), original)
        self.assertFalse((self.workspace / 'resume.previous.md').exists())

    def test_save_and_build_share_busy_lock(self):
        original = self.state.draft.read_bytes()
        self.state.lock.acquire()
        try:
            self.assertEqual(self.request('POST', '/api/save', {'source': '# changed', 'revision': 1})[0], 409)
        finally:
            self.state.lock.release()
        self.assertEqual(self.state.draft.read_bytes(), original)
        entered, release = threading.Event(), threading.Event()
        real_save = self.state.save
        def slow_save(source, revision, pages=None, font_size=None, template_id=None):
            entered.set()
            release.wait(timeout=2)
            return real_save(source, revision, pages, font_size, template_id)
        result = []
        with patch.object(self.state, 'save', side_effect=slow_save):
            worker = threading.Thread(target=lambda: result.append(self.request('POST', '/api/save', {'source': '# saved', 'revision': 2})))
            worker.start()
            try:
                self.assertTrue(entered.wait(timeout=2))
                self.assertEqual(self.build()[0], 409)
                self.assertEqual(self.request('POST', '/api/save', {'source': '# competing', 'revision': 3})[0], 409)
            finally:
                release.set()
                worker.join(timeout=3)
        self.assertEqual(result[0][0], 200)
        self.assertEqual(self.state.draft.read_text(encoding='utf-8'), '# saved')

    def test_editor_csp_and_font_allowlist(self):
        status, headers, _ = self.request()
        self.assertEqual(status, 200)
        policy = headers['Content-Security-Policy']
        self.assertIn("script-src 'self';", policy)
        self.assertNotIn('unsafe-eval', policy)
        self.assertIn("style-src 'self' 'unsafe-inline'", policy)
        self.assertIn("img-src 'self' data: blob:", policy)
        self.assertIn("font-src 'self' data:", policy)
        assets_root = Path(self.temp.name) / 'static-skill'
        for relative in ['editor/bundle.js', 'editor/bundle.css', 'editor/resume.css', 'fonts/NotoSansSC-Regular.ttf', 'fonts/NotoSansSC-Bold.ttf']:
            asset = assets_root / 'assets' / relative
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(b'static fixture')
            url = '/editor/' + asset.name if relative.startswith('editor/') else '/assets/' + relative
            with patch.object(preview, 'SKILL', assets_root):
                response = self.request(path=url)
            self.assertEqual(response[0], 200)
            self.assertEqual(response[2], b'static fixture')
        for path in ['/assets/fonts/other.ttf', '/assets/fonts/../editor/app.js', '/assets/fonts/%2e%2e/editor/app.js']:
            self.assertEqual(self.request(path=path)[0], 404)

    def test_font_size_validation_and_persisted_settings(self):
        original = self.state.draft.read_bytes()
        for value in [True, None, '10.5', 7.5, 18.5, 10.1, float('nan'), float('inf')]:
            for endpoint in ['/api/build', '/api/save']:
                with self.subTest(value=value, endpoint=endpoint):
                    data = {'source': '# changed', 'pages': 1, 'revision': 1, 'font_size': value}
                    self.assertEqual(self.request('POST', endpoint, data)[0], 400)
                    self.assertEqual(self.state.draft.read_bytes(), original)
        self.assertEqual(self.request('POST', '/api/save', {'source': '# changed', 'pages': 2, 'font_size': 11, 'revision': 2})[0], 200)
        resumed = preview.EditorState(self.workspace)
        self.assertEqual((resumed.pages, resumed.font_size), (2, 11))
        self.assertEqual(self.request('POST', '/api/save', {'source': '', 'revision': 3})[0], 200)
        session = json.loads(self.request()[2])
        self.assertEqual((session['default_pages'], session['font_size']), (2, 11))
        self.assertEqual(self.state.draft.read_bytes(), b'')
        for pages in [True, 0, 21]:
            self.assertEqual(self.request('POST', '/api/save', {'source': '# bad', 'revision': 4, 'pages': pages})[0], 400)

    def test_template_catalogue_and_persisted_selection_preserve_source(self):
        session = json.loads(self.request()[2])
        self.assertEqual(session['template_id'], 'classic')
        self.assertEqual({item['id'] for item in session['templates']}, {'classic', 'minimal', 'two-column'})
        source = '# My own draft\n\n- Keep this text'
        status, _, _ = self.request('POST', '/api/save', {'source': source, 'revision': 1, 'template_id': 'minimal'})
        self.assertEqual(status, 200)
        resumed = preview.EditorState(self.workspace)
        self.assertEqual(resumed.template_id, 'minimal')
        self.assertEqual(resumed.draft.read_text(encoding='utf-8'), source)
        self.assertEqual(json.loads(self.state.settings_file.read_text())['template_id'], 'minimal')
        self.request('POST', '/api/save', {'source': source, 'revision': 2})
        self.assertEqual(self.state.template_id, 'minimal')
        with patch.object(self.state, 'compile', return_value={'ok': True}) as compile_mock:
            self.build(source=source)
        self.assertEqual(compile_mock.call_args.args[-1], 'minimal')

    def test_old_settings_default_to_classic(self):
        self.state.settings_file.write_text(json.dumps({'pages': 2, 'font_size': 11}))
        resumed = preview.EditorState(self.workspace)
        self.assertEqual((resumed.pages, resumed.font_size, resumed.template_id), (2, 11, 'classic'))

    def test_invalid_templates_never_overwrite_draft_or_settings(self):
        original = self.state.draft.read_bytes()
        for value in ['unknown', '../minimal', 'minimal.tex', '', None, True, {}, ['classic']]:
            for endpoint in ['/api/build', '/api/save']:
                with self.subTest(value=value, endpoint=endpoint):
                    status, _, _ = self.request('POST', endpoint, {'source': '# changed', 'revision': 1, 'pages': 1, 'template_id': value})
                    self.assertEqual(status, 400)
                    self.assertEqual(self.state.draft.read_bytes(), original)
                    self.assertFalse(self.state.settings_file.exists())
        with self.assertRaises(ValueError):
            self.state.compile('# changed', 1, 1, template_id='../classic')
        self.assertEqual(self.state.draft.read_bytes(), original)

    def test_template_forwarded_and_build_result_bound_to_selection(self):
        def fake_compile(command):
            self.assertEqual(command[command.index('--template') + 1], 'two-column')
            return subprocess.CompletedProcess(command, 1, '', 'syntax error')
        with patch.object(preview, 'run_compile', side_effect=fake_compile):
            status, _, body = self.build(template_id='two-column')
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['template_id'], 'two-column')
        self.assertEqual(self.state.template_id, 'two-column')
        with patch.object(preview, 'run_compile', side_effect=subprocess.TimeoutExpired('build', 600)):
            self.assertEqual(self.state.compile('# x', 1, 2, template_id='minimal')['template_id'], 'minimal')

    def test_local_logo_route_uses_catalogue_resolver(self):
        image = Path(self.temp.name) / 'school.svg'
        image.write_bytes(b'<svg/>')
        entries = {'school': {'id': 'school', 'file': 'school.svg', 'local': True}}
        with patch.object(preview.logo_assets, 'catalogue', return_value=entries), patch.object(preview.logo_assets, 'resolve_logo_path', return_value=image, create=True) as resolver:
            self.assertEqual(json.loads(self.request()[2])['logos'], [dict(entries['school'], aspect_ratio=1)])
            resolver.assert_called_once_with('school.svg')
            resolver.reset_mock()
            self.assertEqual(self.request(path='/assets/logos/school.svg')[2], b'<svg/>')
            resolver.assert_called_once_with('school.svg')
            self.assertEqual(self.request(path='/assets/logos/local/school.svg')[0], 404)
        with patch.object(preview.logo_assets, 'catalogue', return_value=entries), patch.object(preview.logo_assets, 'resolve_logo_path', side_effect=ValueError('checksum mismatch'), create=True):
            self.assertEqual(self.request(path='/assets/logos/school.svg')[0], 404)

    def test_template_thumbnail_allowlist(self):
        assets_root = Path(self.temp.name) / 'thumbnail-skill'
        image = assets_root / 'assets/templates/thumbnails/minimal.png'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'public thumbnail')
        with patch.object(preview, 'SKILL', assets_root):
            status, headers, body = self.request(path='/assets/templates/thumbnails/minimal.png')
        self.assertEqual((status, body), (200, b'public thumbnail'))
        self.assertEqual(headers['Content-Type'], 'image/png')
        for path in ['/assets/templates/minimal.tex', '/assets/templates/thumbnails/unknown.png',
                     '/assets/templates/thumbnails/../minimal.tex', '/assets/templates/thumbnails/%2e%2e/minimal.tex',
                     '/assets/templates/thumbnails/minimal.png/extra', '/assets/templates/thumbnails/%6dinimal.png']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path=path)[0], 404)

    def test_inline_formatting_persists_in_markdown_and_global_font_range(self):
        source = '# Name\n## Work\n- <size:18>**文字**</size> ![logo:bupt@28] 大校徽'
        for revision, font_size in enumerate([8, 18]):
            status, _, _ = self.request('POST', '/api/save', {'source': source, 'revision': revision, 'font_size': font_size})
            self.assertEqual(status, 200)
            resumed = preview.EditorState(self.workspace)
            self.assertEqual(resumed.font_size, font_size)
            self.assertEqual(resumed.draft.read_text(encoding='utf-8'), source)
            self.assertEqual(set(json.loads(resumed.settings_file.read_text())), {'pages', 'font_size', 'template_id'})

    def test_build_forwards_font_size_to_compiler(self):
        def fake_compile(command):
            self.assertEqual(command[command.index('--font-size') + 1], '9.5')
            return subprocess.CompletedProcess(command, 1, '', '')
        with patch.object(preview, 'run_compile', side_effect=fake_compile):
            self.assertEqual(self.build(font_size=9.5)[0], 400)
        self.assertEqual(self.state.font_size, 9.5)

    def test_build_forwards_snapshot_and_report(self):
        result = {'ok': True, 'revision': 7, 'source_saved': True, 'report': {'passed': True}, 'previews': ['/builds/' + 'a' * 32 + '/preview-1.png'], 'pdf_url': '/builds/' + 'a' * 32 + '/resume.pdf'}
        with patch.object(self.state, 'compile', return_value=result) as compile_mock:
            status, _, body = self.build()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), result)
        compile_mock.assert_called_once_with('# 测试\n## 经历\n- 新内容', 1, 7, 10.5, 'classic')

    def test_compile_error_preserves_new_and_previous_drafts(self):
        previous = self.state.draft.read_text(encoding='utf-8')
        with patch.object(preview, 'run_compile', return_value=subprocess.CompletedProcess([], 1, 'bad syntax', '')):
            status, _, body = self.build(source='# invalid **')
        result = json.loads(body)
        self.assertEqual(status, 400)
        self.assertFalse(result['ok'])
        self.assertTrue(result['source_saved'])
        self.assertIsNone(result['pdf_url'])
        self.assertEqual(result['revision'], 7)
        self.assertIn('bad syntax', result['log'])
        self.assertEqual(self.state.draft.read_text(encoding='utf-8'), '# invalid **')
        self.assertEqual((self.workspace / 'resume.previous.md').read_text(encoding='utf-8'), previous)

    def test_verified_compile_returns_only_matching_build_artifacts(self):
        def fake_compile(command, **kwargs):
            output = Path(command[command.index('--output') + 1])
            output.mkdir()
            (output / 'verification.json').write_text(json.dumps({'passed': True, 'previews': ['/private/path']}))
            (output / 'resume.pdf').write_bytes(b'%PDF-test')
            (output / 'preview-1.png').write_bytes(b'PNG-test')
            (output / 'preview-10.png').write_bytes(b'PNG-ten')
            (output / 'preview-2.png').write_bytes(b'PNG-two')
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(preview, 'run_compile', side_effect=fake_compile):
            status, _, body = self.build()
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(result['source_saved'])
        self.assertEqual(result['template_id'], 'classic')
        self.assertNotIn('previews', result['report'])
        self.assertEqual(self.request(path=result['pdf_url'])[2], b'%PDF-test')
        self.assertEqual(self.request(path=result['previews'][0])[2], b'PNG-test')
        self.assertNotIn('Content-Disposition', self.request(path=result['previews'][0])[1])
        self.assertIn('attachment; filename="preview-1.png"', self.request(path=result['previews'][0] + '?download=1')[1]['Content-Disposition'])
        status, headers, body = self.request(path=f"/builds/{result['build_id']}/previews.zip")
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'application/zip')
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertEqual(archive.namelist(), ['preview-1.png', 'preview-2.png', 'preview-10.png'])
            self.assertEqual(archive.read('preview-2.png'), b'PNG-two')
        self.assertEqual(result['previews'], [f"/builds/{result['build_id']}/preview-{number}.png" for number in [1, 2, 10]])

    def test_timeout_preserves_draft_and_releases_lock(self):
        with patch.object(preview, 'run_compile', side_effect=subprocess.TimeoutExpired('tectonic', 600)):
            status, _, body = self.build(source='# timeout draft')
        self.assertEqual(status, 400)
        self.assertTrue(json.loads(body)['source_saved'])
        self.assertEqual(self.state.draft.read_text(encoding='utf-8'), '# timeout draft')
        self.assertFalse(self.state.lock.locked())


    def test_missing_cache_retries_online_but_syntax_errors_do_not(self):
        missing = subprocess.CompletedProcess([], 1, '', "error: this bundle isn't cached")
        failure = subprocess.CompletedProcess([], 1, '', 'syntax error')
        with patch.object(preview, 'run_compile', side_effect=[missing, failure]) as run:
            self.state.compile('# test', 1, 0)
        self.assertEqual(run.call_count, 2)
        self.assertIn('--only-cached', run.call_args_list[0].args[0])
        self.assertNotIn('--only-cached', run.call_args_list[1].args[0])
        with patch.object(preview, 'run_compile', return_value=failure) as run:
            self.state.compile('# test', 1, 1)
        self.assertEqual(run.call_count, 1)

    def test_compiler_output_uses_utf8(self):
        result = preview.run_compile([sys.executable, '-c', "print('中文诊断')"], timeout=30)
        self.assertEqual(result.stdout.strip(), '中文诊断')
        self.assertEqual(result.returncode, 0)

    def test_windows_timeout_kills_process_tree(self):
        process = Mock(pid=123)
        process.communicate.side_effect = [subprocess.TimeoutExpired('build', 1), ('', '')]
        process.poll.return_value = None
        with patch.object(preview, 'IS_WINDOWS', True), patch.object(preview.subprocess, 'Popen', return_value=process) as start, patch.object(preview.subprocess, 'run') as kill_tree:
            with self.assertRaises(subprocess.TimeoutExpired):
                preview.run_compile(['python', 'build.py'], timeout=1)
        self.assertFalse(start.call_args.kwargs['start_new_session'])
        kill_tree.assert_called_once_with(['taskkill', '/PID', '123', '/T', '/F'], capture_output=True, check=False)
        process.kill.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)

    @unittest.skipUnless(os.name == 'posix', 'Process group lifecycle is POSIX-specific')
    def test_timeout_stops_compiler_grandchildren(self):
        pidfile = Path(self.temp.name) / 'child.pid'
        child = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
        parent = (
            "import pathlib,subprocess,sys,time; "
            f"p=subprocess.Popen([sys.executable, '-c', {child!r}]); "
            f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); "
            "time.sleep(60)"
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            preview.run_compile([sys.executable, '-c', parent], timeout=10)
        self.assertTrue(pidfile.exists())
        pid = int(pidfile.read_text(encoding='utf-8'))
        # A killed child may briefly remain a zombie until init reaps it.
        for _ in range(30):
            result = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True)
            if result.returncode or result.stdout.strip().startswith('Z'):
                break
            time.sleep(0.05)
        else:
            os.kill(pid, signal.SIGKILL)
            self.fail('Compiler grandchild survived the timeout')

    def test_busy_build_does_not_overwrite_draft(self):
        original = self.state.draft.read_bytes()
        self.state.lock.acquire()
        try:
            with patch.object(self.state, 'compile') as compile_mock:
                self.assertEqual(self.build()[0], 409)
                compile_mock.assert_not_called()
        finally:
            self.state.lock.release()
        self.assertEqual(self.state.draft.read_bytes(), original)

    def test_path_allowlist_blocks_workspace_and_traversal(self):
        for path in ['/resume.md', '/builds/../resume.md', '/builds/' + 'a' * 32 + '/../resume.md', '/builds/' + 'a' * 32 + '/verification.json', '/assets/logos/../../scripts/preview.py', '/assets/logos/%2e%2e%2fscripts%2fpreview.py', '/%2e%2e/LICENSE']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path=path)[0], 404)

    def test_workspace_resume_and_conflicting_import(self):
        self.state.draft.write_text('# persisted draft')
        resumed = preview.EditorState(self.workspace)
        self.assertEqual(resumed.draft.read_text(encoding='utf-8'), '# persisted draft')
        incoming = Path(self.temp.name) / 'incoming.md'
        incoming.write_text('# conflicting source')
        with self.assertRaisesRegex(ValueError, 'different draft'):
            preview.EditorState(self.workspace, incoming)
        self.assertEqual(self.state.draft.read_text(encoding='utf-8'), '# persisted draft')
        incoming.write_text('# persisted draft')
        self.assertEqual(preview.EditorState(self.workspace, incoming).draft.read_text(encoding='utf-8'), '# persisted draft')


if __name__ == '__main__':
    unittest.main()
