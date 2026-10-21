"""Local editor HTTP and draft lifecycle regression tests (no TeX/browser)."""
import http.client
import importlib.util
import json
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

    def test_build_forwards_snapshot_and_report(self):
        result = {'ok': True, 'revision': 7, 'source_saved': True, 'report': {'passed': True}, 'previews': ['/builds/' + 'a' * 32 + '/preview-1.png'], 'pdf_url': '/builds/' + 'a' * 32 + '/resume.pdf'}
        with patch.object(self.state, 'compile', return_value=result) as compile_mock:
            status, _, body = self.build()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), result)
        compile_mock.assert_called_once_with('# 测试\n## 经历\n- 新内容', 1, 7)

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
        self.assertNotIn('previews', result['report'])
        self.assertEqual(self.request(path=result['pdf_url'])[2], b'%PDF-test')
        self.assertEqual(self.request(path=result['previews'][0])[2], b'PNG-test')
        self.assertEqual(result['previews'], [f"/builds/{result['build_id']}/preview-{number}.png" for number in [1, 2, 10]])

    def test_timeout_preserves_draft_and_releases_lock(self):
        with patch.object(preview, 'run_compile', side_effect=subprocess.TimeoutExpired('tectonic', 600)):
            status, _, body = self.build(source='# timeout draft')
        self.assertEqual(status, 400)
        self.assertTrue(json.loads(body)['source_saved'])
        self.assertEqual(self.state.draft.read_text(encoding='utf-8'), '# timeout draft')
        self.assertFalse(self.state.lock.locked())


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
