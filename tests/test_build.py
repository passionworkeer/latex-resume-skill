import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills/latex-resume/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load('build')
verify = load('verify')


class MarkdownTests(unittest.TestCase):
    def test_unicode_and_visible_link_text(self):
        tex, expected = build.convert('# 示例 Ω\n邮箱 · [主页](https://example.com/a?q=1&b=2)\n## 经历\n### 机构 | 开发者 | 2025–2026\n- **中文**与 café 100%\n')
        self.assertIn('中文与 café 100%', expected)
        self.assertNotIn('https://', expected)
        self.assertIn(r'100\%', tex)
        self.assertIn(r'\href{https://example.com/a?q=1\&b=2}{主页}', tex)
        self.assertIn('机构 开发者 2025–2026', expected)

    def test_raw_tex_is_literal(self):
        value, visible = build.inline(r'\input{secrets} $HOME_#&%~^')
        self.assertEqual(visible, r'\input{secrets} $HOME_#&%~^')
        self.assertIn(r'\textbackslash{}input\{secrets\}', value)
        self.assertIn(r'\$HOME\_\#\&\%\textasciitilde{}\textasciicircum{}', value)

    def test_reject_unsupported_and_malformed(self):
        for source in ['text', '# A\n# B', '# A\n## B\n### only title', '# A\n## B\n- **open', '# A\n## B\n1. numbered', '# A\n## B\n  - nested', '# A\n## B\n![image](https://example.com)', '# A\n## B\n`code`', '# A\n## B\n[label](javascript:bad)']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                build.convert(source)

    def test_whitespace_bullets_only_are_ignored(self):
        self.assertTrue(verify.compare('中文 A\nB', '中文 • A B')['exact_text_match'])
        for actual in ['中文 A', '中 A B', '中文 A B extra', '中文 A-B']:
            self.assertFalse(verify.compare('中文 A B', actual)['exact_text_match'])


class VerificationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.pdf = self.directory / 'sample.pdf'
        self.pdf.write_bytes(b'mocked PDF bytes for hash verification')

    def run_check(self, *, warnings='Compilation completed', x0=10, pages=1, expected='ABC'):
        from types import SimpleNamespace
        from unittest.mock import patch, MagicMock
        chars = [dict(text=c, x0=x0, x1=x0 + 5, top=10, bottom=20) for c in 'ABC']
        page = SimpleNamespace(chars=chars, width=595, height=842)
        context = MagicMock()
        context.__enter__.return_value = SimpleNamespace(pages=[page] * pages)
        module = SimpleNamespace(open=lambda _: context)
        log = self.directory / 'resume.log'
        log.write_text(warnings)
        with patch.dict('sys.modules', {'pdfplumber': module}):
            return verify.check(self.pdf, expected, 1, log)[0]

    def test_font_missing_and_overflow_diagnostics_fail(self):
        self.assertTrue(self.run_check()['passed'])
        for warning in ['Missing character: There is no glyph', 'LaTeX Font Warning: shape substituted', r'Overfull \hbox (3pt too wide)', r'Overfull \vbox (2pt too high)']:
            with self.subTest(warning=warning):
                report = self.run_check(warnings=warning)
                self.assertFalse(report['passed'])
                self.assertEqual(report['font_and_overflow_warnings'], [warning])

    def test_bounds_page_count_and_text_fail_independently(self):
        self.assertTrue(self.run_check(x0=-2)['out_of_page_glyphs'])
        self.assertFalse(self.run_check(x0=-2)['passed'])
        self.assertFalse(self.run_check(pages=2, expected='ABCABC')['passed'])
        self.assertFalse(self.run_check(expected='ABCD')['passed'])

    def test_provided_missing_log_fails(self):
        from types import SimpleNamespace
        from unittest.mock import patch, MagicMock
        context = MagicMock()
        context.__enter__.return_value = SimpleNamespace(pages=[])
        with patch.dict('sys.modules', {'pdfplumber': SimpleNamespace(open=lambda _: context)}):
            with self.assertRaises(ValueError):
                verify.check(self.pdf, '', log_path=self.directory / 'absent.log')
            report, _ = verify.check(self.pdf, '')
            self.assertFalse(report['log_checked'])

    def test_cleanup_invalidates_results_preserves_unrelated_files(self):
        stale = ['resume.pdf', 'resume.log', 'build.log', 'verification.json', 'verification.extracted.txt', 'preview-1.png', 'preview-02.png']
        for name in stale + ['notes.txt', 'preview-custom.png']:
            (self.directory / name).write_text('preserve or invalidate')
        build.clear_previous_results(self.directory, self.directory / 'input.md')
        self.assertTrue(all(not (self.directory / name).exists() for name in stale))
        self.assertTrue((self.directory / 'notes.txt').exists())
        self.assertTrue((self.directory / 'preview-custom.png').exists())

    def test_cleanup_never_removes_source_or_symlink_target(self):
        original = self.pdf.read_bytes()
        (self.directory / 'resume.pdf').symlink_to(self.pdf)
        with self.assertRaises(ValueError):
            build.clear_previous_results(self.directory, self.pdf.resolve())
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertTrue((self.directory / 'resume.pdf').is_symlink())


if __name__ == '__main__':
    unittest.main()
