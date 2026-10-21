"""Fixed, local LaTeX template catalogue; never resolve user-supplied paths."""

_TEMPLATES = (
    dict(id='classic', name='经典单栏', description='紧凑单栏，适合中文工程师简历', filename='resume.tex', source='https://github.com/zheyuye/resume-chinese', license='MIT'),
    dict(id='minimal', name='简洁单栏', description='清晰标题与舒展留白，适合简洁履历', filename='minimal.tex', source='https://github.com/sb2nov/resume/tree/7b70fe14876f97180034787f2a7f661597416a17', license='MIT'),
    dict(id='two-column', name='彩色双栏', description='蓝色标题与左右双栏，适合分组展示经历与技能', filename='two-column.tex', source='https://github.com/jankapunkt/latexcv/tree/1fc7a2033ddda0fa77003444cafcf96117ad58dd/two_column', license='MIT'),
)


def catalogue():
    return [dict(item, thumbnail=f"{item['id']}.png") for item in _TEMPLATES]


def get_template(template_id='classic'):
    for item in catalogue():
        if type(template_id) is str and item['id'] == template_id:
            return item
    raise ValueError('Unknown template; choose classic, minimal, or two-column')
