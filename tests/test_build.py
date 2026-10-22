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
    def test_body_font_size_preserves_fixed_template_headings(self):
        for size in [8, 8.5, 9, 10.5, 12, 15.5, 18]:
            tex, _ = build.convert('# Name\n## Experience\n- Work', size)
            self.assertIn(r'\fontsize{' + f'{size:g}' + '}{', tex)
            self.assertIn(r'\fontsize{12}{16}', tex)
            self.assertIn(r'\fontsize{16}{21}', tex)
            self.assertNotIn('%%FONT_SIZE%%', tex)
            self.assertNotIn('%%LINE_HEIGHT%%', tex)
        self.assertIn(r'\fontsize{10.5}{13.8}', build.convert('# Name')[0])
        for size in [True, '10.5', 7.5, 18.5, 10.1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                build.convert('# Name', size)

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

    def test_inline_sizes_bold_and_escaped_literal_text(self):
        tex, visible = build.inline(r'<size:16>中文**重点<size:12.5>小字</size>**尾</size> **粗<size:20>大字</size>**')
        self.assertEqual(visible, '中文重点小字尾 粗大字')
        for fragment in [r'\fontsize{16}{', r'\fontsize{12.5}{', r'\fontsize{20}{', r'\textbf{']:
            self.assertIn(fragment, tex)
        text = r'\*\[\]\\\<\>\|\#\`\!\{\}\_\~'
        tex, visible = build.inline(text)
        self.assertEqual(visible, '*[]\\<>|#`!{}_~')
        self.assertIn(r'\textbackslash{}', tex)
        _, expected = build.convert(r'# Name' + '\n## Work\n' + r'### A\|B | C\\ | 2026' + '\n- ' + text)
        self.assertIn('A|B C\\ 2026', expected)
        self.assertIn(visible, expected)
        self.assertIn('ordinary text', build.convert('# Name\n## Work\n   ordinary text')[1])

    def test_inline_sizes_bounds_and_nesting_are_strict(self):
        for size in ['8', '8.5', '32']:
            self.assertEqual(build.inline(f'<size:{size}>text</size>')[1], 'text')
        for token in ['<size:7.5>x</size>', '<size:32.5>x</size>', '<size:12.1>x</size>',
                      '<size:nan>x</size>', '<size:12>x', '<size:12></size>',
                      '**<size:12>x**</size>', '<script>x</script>', '</size>',
                      '<size:12>' * 17 + 'x' + '</size>' * 17]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                build.inline(token)
        self.assertEqual(build.inline('<size:12>' * 16 + 'x' + '</size>' * 16)[1], 'x')

    def test_links_support_formatted_labels_mailto_and_escaped_parentheses(self):
        tex, visible = build.inline(r'[**<size:12>联系\[我\]</size>**](mailto:a@example.com) [项目](https://example.com/a\(b\))')
        self.assertEqual(visible, '联系[我] 项目')
        self.assertIn(r'\href{mailto:a@example.com}', tex)
        self.assertIn(r'\href{https://example.com/a(b)}', tex)
        for token in ['[x](javascript:alert)', '[x](https://example.com/a(b))', '[x](https://example.com/\\evil)',
                      '[<size:12>' * 17 + 'x' + '</size>](https://example.com)' * 17]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                build.inline(token)

    def test_avatar_support_in_markdown_and_templates(self):
        source = '# 示例姓名\n![avatar:avatar.png]\n后端开发 | example@example.com | [个人主页](https://example.com)\n## 教育背景\n### 示例大学 | 软件工程 | 2021-2025\n'
        tex, expected = build.convert(source)
        self.assertIn(r'\resumeheader[avatar.png]{示例姓名}{后端开发 | example@example.com | \href{https://example.com}{个人主页}}', tex)
        self.assertNotIn('avatar.png', expected)
        self.assertNotIn('![avatar', expected)
        self.assertIn('示例姓名', expected)
        self.assertIn('个人主页', expected)
        tex2, _ = build.convert('# 张三\n电话 | 邮箱\n## 经历\n- 工作', avatar='photo.jpg')
        self.assertIn(r'\resumeheader[photo.jpg]{张三}{电话 | 邮箱}', tex2)
        tex3, _ = build.convert('# 李四\n电话\n## 经历\n- 工作')
        self.assertIn(r'\resumename{李四}', tex3)
        self.assertIn(r'\contact{电话}', tex3)

    def test_avatar_adversarial_validation_and_resolution(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            workspace = root / 'workspace'
            workspace.mkdir()
            snapshots = workspace / 'snapshots'
            snapshots.mkdir()
            img = Image.new('RGB', (100, 100), color=(100, 150, 200))
            avatar_file = workspace / 'photo.png'
            img.save(avatar_file)

            source_file = snapshots / 'build.md'
            source_file.write_text('# 姓名\n![avatar:photo.png]\n电话\n## 经历\n- 工作\n', encoding='utf-8')
            tex, _ = build.convert(source_file.read_text(encoding='utf-8'))
            self.assertIn(r'\resumeheader[photo.png]', tex)

            # Test parent directory resolution as done in main
            avatar_src = Path('photo.png')
            candidate = (source_file.parent / avatar_src).resolve()
            self.assertFalse(candidate.is_file())
            resolved = (source_file.parent.parent / avatar_src).resolve()
            self.assertTrue(resolved.is_file())

            # Test invalid formats are rejected
            bad_file = workspace / 'script.sh'
            bad_file.write_text('echo bad')
            with self.assertRaises(ValueError):
                ext = bad_file.suffix.lower()
                if ext not in {'.png', '.jpg', '.jpeg', '.pdf'}:
                    raise ValueError(f'Unsupported avatar format: {ext}')

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

    def test_cleanup_removes_generated_avatar(self):
        (self.directory / 'avatar.png').write_bytes(b'fake png')
        (self.directory / 'avatar.jpg').write_bytes(b'fake jpg')
        build.clear_previous_results(self.directory, self.directory / 'input.md')
        self.assertFalse((self.directory / 'avatar.png').exists())
        self.assertFalse((self.directory / 'avatar.jpg').exists())

    def test_cleanup_never_removes_source_or_symlink_target(self):
        original = self.pdf.read_bytes()
        (self.directory / 'resume.pdf').symlink_to(self.pdf)
        with self.assertRaises(ValueError):
            build.clear_previous_results(self.directory, self.pdf.resolve())
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertTrue((self.directory / 'resume.pdf').is_symlink())


if __name__ == '__main__':
    unittest.main()
