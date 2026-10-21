import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/latex-resume/scripts'
sys.path.insert(0, str(SCRIPTS))
import logos
import build


class LogoTests(unittest.TestCase):
    def test_catalogue_hashes_and_all_svg_shapes(self):
        entries = logos.catalogue()
        self.assertGreater(len(entries), 20)
        for slug, entry in entries.items():
            with self.subTest(slug=slug):
                raw = (logos.DIRECTORY / entry['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
                logos.validate_svg(raw)

    def test_logo_is_decorative_and_unknown_ids_fail(self):
        tex, expected = build.convert('# 示例\n## 经历\n### ![logo:github] 示例机构 | 开发 | 2025\n- ![logo:docker] 工具\n')
        self.assertIn(r'\resumeicon{github}', tex)
        self.assertNotIn('logo:', expected)
        self.assertIn('示例机构 开发 2025', expected)
        for token in ['![logo:missing-brand]', '![logo:../github]', '![logo:github](https://example.com)']:
            with self.subTest(token=token):
                if token.endswith('(https://example.com)'):
                    # A valid logo followed by literal text is not an image/network fetch.
                    self.assertNotIn(r'\includegraphics{https', build.inline(token)[0])
                else:
                    with self.assertRaises(ValueError):
                        build.inline(token)

    def test_active_or_external_svg_rejected(self):
        for content in ['<svg><script>alert(1)</script></svg>', '<svg onload="run()"/>', '<svg><image href="file:///private"/></svg>', '<svg><path fill="url(https://example.com/x)"/></svg>', '<svg><foreignObject/></svg>', '<!DOCTYPE svg [<!ENTITY x "x">]><svg/>']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                logos.validate_svg(content.encode())

    def test_all_logos_convert_to_pdf_with_provenance(self):
        import fitz
        with tempfile.TemporaryDirectory() as folder:
            logos.prepare(logos.catalogue().keys(), folder)
            target = Path(folder) / 'logos'
            for slug in logos.catalogue():
                with fitz.open(target / (slug + '.pdf')) as document:
                    self.assertEqual(len(document), 1)
                    self.assertEqual(document[0].get_text().strip(), '')
            self.assertTrue((target / 'SOURCES.json').is_file())
            self.assertTrue((target / 'LICENSE.simple-icons.md').is_file())


if __name__ == '__main__':
    unittest.main()
