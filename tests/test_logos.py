import hashlib
import json
from unittest.mock import patch
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
                raw = logos.resolve_logo_path(entry['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
                logos.validate_svg(raw)

    def test_local_school_registry_and_presentation_normalization(self):
        import fetch_school_logos as schools
        raw = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path style="fill:#039;stroke:none" d="M0 0h24v24H0z"/></svg>'
        safe = schools.normalize_svg(raw)
        self.assertNotIn(b'style=', safe)
        self.assertIn(b'#039', safe)
        for bad in [b'<svg><path style="fill:url(https://example.com/x)"/></svg>', b'<svg><script/></svg>', b'<svg><path style="unknown:1"/></svg>']:
            with self.assertRaises(ValueError):
                schools.normalize_svg(bad)
        with tempfile.TemporaryDirectory() as folder, patch.object(logos, 'DIRECTORY', Path(folder)):
            root = Path(folder)
            (root/'manifest.json').write_text(json.dumps({'icons': []}))
            (root/'local').mkdir()
            (root/'local/bupt.svg').write_bytes(safe)
            local = {'id': 'bupt', 'file': 'bupt.svg', 'sha256': hashlib.sha256(safe).hexdigest()}
            (root/'local/manifest.json').write_text(json.dumps({'icons': [local]}))
            self.assertTrue(logos.catalogue()['bupt']['local'])
            self.assertEqual(logos.resolve_logo_path('bupt.svg'), root/'local/bupt.svg')
            for name in ['../bupt.svg', 'unknown.svg']:
                with self.assertRaises(ValueError):
                    logos.resolve_logo_path(name)
            (root/'local/bupt.svg').write_bytes(b'<svg/>')
            with self.assertRaises(ValueError):
                logos.resolve_logo_path('bupt.svg')
            (root/'local/bupt.svg').unlink()
            (root/'local/bupt.svg').symlink_to(root/'manifest.json')
            with self.assertRaises(ValueError):
                logos.resolve_logo_path('bupt.svg')

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
