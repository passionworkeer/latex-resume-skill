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

    def test_bundled_school_wins_over_legacy_local_and_copies_rights(self):
        public = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>'
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as output, patch.object(logos, 'DIRECTORY', Path(folder)):
            root = Path(folder)
            (root / 'schools').mkdir()
            (root / 'local').mkdir()
            item = {'id': 'bupt', 'file': 'bupt.svg', 'storage': 'schools', 'sha256': hashlib.sha256(public).hexdigest()}
            (root / 'manifest.json').write_text(json.dumps({'icons': [item]}))
            (root / 'schools/bupt.svg').write_bytes(public)
            for name in ['SOURCES.json', 'RIGHTS.md', 'LICENSE.upstream-collection.txt']:
                (root / 'schools' / name).write_text('school provenance')
            for name in ['LICENSE.simple-icons.md', 'DISCLAIMER.simple-icons.md']:
                (root / name).write_text('icon license')
            (root / 'local/manifest.json').write_text(json.dumps({'icons': [dict(item, sha256='old-download')]}))
            (root / 'local/bupt.svg').write_bytes(b'legacy private bytes')
            self.assertEqual(logos.catalogue()['bupt']['storage'], 'schools')
            self.assertEqual(logos.resolve_logo_path('bupt.svg').read_bytes(), public)
            logos.prepare(['bupt'], output)
            self.assertEqual((Path(output) / 'logos/bupt.svg').read_bytes(), public)
            self.assertEqual((Path(output) / 'logos/SCHOOL-RIGHTS.md').read_text(), 'school provenance')
            self.assertTrue((Path(output) / 'logos/SCHOOL-SOURCES.json').is_file())
            self.assertTrue((Path(output) / 'logos/SCHOOL-LICENSE.upstream-collection.txt').is_file())
            self.assertEqual((root / 'local/bupt.svg').read_bytes(), b'legacy private bytes')
            (root / 'schools/bupt.svg').unlink()
            (root / 'schools/bupt.svg').symlink_to(root / 'manifest.json')
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

    def test_logo_size_is_independent_and_bounded(self):
        tex, visible = build.inline('![logo:github@8] small ![logo:github@48] large ![logo:github] default')
        self.assertIn(r'\resumeicon[8]{github}', tex)
        self.assertIn(r'\resumeicon[48]{github}', tex)
        self.assertIn(r'\resumeicon{github}', tex)
        self.assertEqual(visible, ' small  large  default')
        self.assertEqual(logos.TOKEN.match('![logo:github@20.5]').groups(), ('github', '20.5'))
        self.assertEqual(build.inline(r'\!\[logo:github@20\]')[1], '![logo:github@20]')
        for size in ['7.5', '48.5', '12.1', 'nan', '-10', '10pt', '']:
            with self.subTest(size=size), self.assertRaises(ValueError):
                build.inline(f'![logo:github@{size}]')
        for template_id in ['classic', 'minimal', 'two-column']:
            tex, _ = build.convert('# Name\n## Work\n- ![logo:github@20.5] Work', template_id=template_id)
            self.assertIn(r'\newcommand{\resumeicon}[2][10.5]', tex)
            self.assertIn(r'height=#1pt', tex)

    def test_active_or_external_svg_rejected(self):
        for content in ['<svg><script>alert(1)</script></svg>', '<svg onload="run()"/>', '<svg><image href="file:///private"/></svg>', '<svg><path fill="url(https://example.com/x)"/></svg>', '<svg><foreignObject/></svg>', '<!DOCTYPE svg [<!ENTITY x "x">]><svg/>']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                logos.validate_svg(content.encode())

    def test_custom_logo_auto_discovery_and_build(self):
        svg_content = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>'
        with tempfile.TemporaryDirectory() as folder, patch.object(logos, 'DIRECTORY', Path(folder)):
            root = Path(folder)
            (root / 'manifest.json').write_text(json.dumps({'icons': []}))
            (root / 'custom').mkdir()
            (root / 'custom/my-company.svg').write_bytes(svg_content)
            cat = logos.catalogue()
            self.assertIn('my-company', cat)
            self.assertEqual(cat['my-company']['storage'], 'custom')
            self.assertTrue(cat['my-company']['custom'])
            resolved = logos.resolve_logo_path('my-company.svg')
            self.assertEqual(resolved, root / 'custom/my-company.svg')

    def test_add_custom_logo_cli_and_adversarial_rejection(self):
        import subprocess
        safe_svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>'
        evil_svg = b'<svg><script>alert("evil")</script></svg>'
        script_path = SCRIPTS / 'add_custom_logo.py'
        with tempfile.TemporaryDirectory() as folder:
            temp_root = Path(folder)
            safe_file = temp_root / 'good.svg'
            safe_file.write_bytes(safe_svg)
            evil_file = temp_root / 'evil.svg'
            evil_file.write_bytes(evil_svg)
            res_safe = subprocess.run([sys.executable, str(script_path), '--file', str(safe_file), '--id', 'mytestcorp'], capture_output=True, text=True)
            self.assertEqual(res_safe.returncode, 0)
            custom_installed = SCRIPTS.parent / 'assets/logos/custom/mytestcorp.svg'
            self.assertTrue(custom_installed.is_file())
            custom_installed.unlink(missing_ok=True)
            res_evil = subprocess.run([sys.executable, str(script_path), '--file', str(evil_file), '--id', 'evilcorp'], capture_output=True, text=True)
            self.assertNotEqual(res_evil.returncode, 0)
            self.assertIn('Error:', res_evil.stderr)

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
