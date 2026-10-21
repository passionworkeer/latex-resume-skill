import sys
from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/latex-resume/scripts'
sys.path.insert(0, str(SCRIPTS))
from templates import catalogue, get_template
from build import convert


class TemplateTests(unittest.TestCase):
    def test_catalogue_whitelist_and_copy(self):
        self.assertEqual([t['id'] for t in catalogue()], ['classic', 'minimal', 'two-column'])
        for value in ['../resume.tex', '/tmp/a.tex', '', None, True, ['classic']]:
            with self.assertRaises(ValueError):
                get_template(value)
        items = catalogue()
        items[0]['filename'] = '/tmp/evil'
        self.assertEqual(get_template()['filename'], 'resume.tex')

    def test_every_layout_preserves_identical_content_and_font_size(self):
        source = '# Example 示例\nContact 联系\n## Experience 经历\n### Company 公司 | Role 工程师 | 2026\n- **Bold 加粗** and 100% _ # &\n## Skills 技能\nPython and 中文'
        expected = convert(source)[1]
        layouts = []
        for item in catalogue():
            tex, text = convert(source, 11, item['id'])
            self.assertEqual(text, expected)
            self.assertIn(r'\fontsize{11}{', tex)
            self.assertIn(r'\textbf{Bold 加粗}', tex)
            self.assertNotIn('%%BODY%%', tex)
            self.assertTrue((SCRIPTS.parent / 'assets/templates' / item['filename']).is_file())
            layouts.append(tex)
        self.assertEqual(len(set(layouts)), 3)
        tex, _ = convert('# Name\ncontact only', template_id='two-column')
        self.assertNotIn(r'\begin{multicols}', tex)
        tex, _ = convert(source, template_id='two-column')
        self.assertEqual(tex.count(r'\begin{multicols}{2}'), 1)
        self.assertEqual(tex.count(r'\end{multicols}'), 1)
