"""Fixed, local LaTeX template catalogue; never resolve user-supplied paths."""

import re
from pathlib import Path

_TEMPLATES = (
    dict(id='classic', name='经典单栏', description='紧凑单栏，适合中文工程师简历', filename='resume.tex', source='https://github.com/zheyuye/resume-chinese', license='MIT'),
    dict(id='minimal', name='简洁单栏', description='清晰标题与舒展留白，适合简洁履历', filename='minimal.tex', source='https://github.com/sb2nov/resume/tree/7b70fe14876f97180034787f2a7f661597416a17', license='MIT'),
    dict(id='two-column', name='彩色双栏', description='蓝色标题与左右双栏，适合分组展示经历与技能', filename='two-column.tex', source='https://github.com/jankapunkt/latexcv/tree/1fc7a2033ddda0fa77003444cafcf96117ad58dd/two_column', license='MIT'),
)


def catalogue():
    return [dict(item, thumbnail=f"{item['id']}.png", layout=layout_metadata(item)) for item in _TEMPLATES]


def get_template(template_id='classic'):
    for item in catalogue():
        if type(template_id) is str and item['id'] == template_id:
            return item
    raise ValueError('Unknown template; choose classic, minimal, or two-column')


def layout_metadata(item):
    """Read the actual bundled TeX metrics for the browser's editable paper."""
    tex = (Path(__file__).resolve().parents[1] / 'assets/templates' / item['filename']).read_text(encoding='utf-8')
    geometry = re.search(r'\\geometry\{([^}]+)\}', tex)[1]
    margins = {side: float(re.search(side + r'=(\d+(?:\.\d+)?)mm', geometry)[1]) for side in ('left', 'right', 'top', 'bottom')}
    name = re.search(r'\\resumename.*?\\fontsize\{([\d.]+)\}\{([\d.]+)\}', tex)
    spacing = re.search(r'\\titlespacing\*.*?\{0pt\}\{([\d.]+)pt\}\{([\d.]+)pt\}', tex)
    colors = {key: '#' + re.search(r'\\definecolor\{' + key + r'\}\{HTML\}\{([A-Fa-f0-9]+)\}', tex)[1] for key in ('bodygray', 'stronggray', 'linkblue')}
    entry = re.search(r'\\newcommand\{\\entry\}.*?\\vspace\{([\d.]+)pt\}', tex)
    return dict(margins=margins, colors=colors, name_size=float(name[1]), name_line=float(name[2]),
                section_before=float(spacing[1]), section_after=float(spacing[2]), entry_before=float(entry[1]),
                columns=2 if item['id']=='two-column' else 1,
                column_gap_mm=8, line_ratio=13.8/10.5, tex_pt_px=96/72.27)


def column_split(weights):
    """Choose a section boundary using visible non-whitespace Unicode characters.

    Kept equivalent to frontend/layout.js; formatting must not move a section.
    """
    if len(weights) < 2:
        return None
    total, prefix = sum(weights), 0
    candidates = []
    for index, weight in enumerate(weights[:-1], 1):
        prefix += weight
        candidates.append((abs(prefix - total / 2), index))
    return min(candidates)[1]
