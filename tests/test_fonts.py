import importlib.util
from pathlib import Path
import tempfile
import unittest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/latex-resume/scripts/setup.py'
spec = importlib.util.spec_from_file_location('resume_setup', SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class FontMappingTests(unittest.TestCase):
    def test_aliases_keep_distinct_unicode_identity_after_save(self):
        font = FontBuilder(1000, isTTF=True)
        font.setupGlyphOrder(['.notdef', 'dot'])
        font.setupCharacterMap({0xB7: 'dot', 0x2022: 'dot', 0x2027: 'dot'})
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0)); pen.lineTo((20, 0)); pen.lineTo((20, 20)); pen.closePath()
        glyph = pen.glyph()
        font.setupGlyf({'.notdef': glyph, 'dot': glyph})
        font.setupHorizontalMetrics({'.notdef': (500, 0), 'dot': (500, 0)})
        font.setupHorizontalHeader(ascent=800, descent=-200)
        font.setupNameTable({'familyName': 'Fictional Test', 'styleName': 'Regular'})
        font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
        font.setupPost()
        setup.preserve_text_cmap(font.font)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'font.ttf'
            font.save(path)
            with TTFont(path) as result:
                cmap = result.getBestCmap()
                self.assertEqual(len({cmap[c] for c in (0xB7, 0x2022, 0x2027)}), 3)
                self.assertEqual(len(result.getGlyphOrder()), len(set(result.getGlyphOrder())))
                for cp in (0xB7, 0x2022, 0x2027):
                    self.assertEqual(result['hmtx'].metrics[cmap[cp]], (500, 0))


if __name__ == '__main__':
    unittest.main()
