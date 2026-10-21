# LaTeX Resume Skill

把简历改稿、项目背景访谈、LaTeX 排版和 PDF 验证交给你的 agent。

这是从实际简历制作流程中整理出的独立小项目：**先核实内容，再组织表达，最后用可编辑的 LaTeX 排版，逐页检查成品**。支持中文和英文，也支持用户提供 PDF / PNG / JPG 作为新模板的版式参考。

仓库只包含虚构示例，**没有作者的真实简历、联系方式、项目经历或历史截图**。自带模板保留我们使用的 A4 单栏、灰色正文、深色重点、黑色分节线和蓝色链接；品牌图标已移除。

![虚构中文简历预览](examples/example-zh.png)

[中文示例 PDF](examples/example-zh.pdf) · [英文示例 PDF](examples/example-en.pdf) · [Skill 入口](skills/latex-resume/SKILL.md) · [完整流程](skills/latex-resume/references/workflow.md)

## 直接复制给 agent

下面整段复制到 Codex、Claude Code 或其他能够读取文件和执行命令的 agent，再发送你的简历即可。无需先手动安装 skill。

```text
请下载 https://github.com/passionworkeer/latex-resume-skill 到一个独立目录（已有时先检查本地修改，避免覆盖）。先阅读 README.md 和 skills/latex-resume/SKILL.md，按文档完成任务。

帮我把接下来提供的简历整理成可编辑 LaTeX 和可投递 PDF。先读取简历，结合我的目标岗位分析内容；可调整表达和结构，但不要编造项目、职责或成果数字。需要更多信息时，针对最影响简历质量的项目背景、本人贡献和验证结果向我提问；已确定的部分继续处理。

缺少 Python、虚拟环境支持、编译器、字体或其他依赖时，请按文档自动检测并安装。优先使用项目内虚拟环境和本地工具；只有环境确实禁止或需要管理员权限时，说明具体阻塞。不要让我手工重复你能完成的安装步骤。

默认先用仓库中的简约单栏模板。如果我发送新的 PDF、PNG 或 JPG 模板，请先观察版式并测量字号、边距、对齐和间距，再用真正可编辑的 LaTeX 重建，不要把整张图当作简历背景，也不要把模板示例人物的经历写进我的简历。

把我的资料、证据、改稿和输出放在 private/ 或 output/ 中。不要提交或发布我的真实简历。生成后检查正文是否丢失、页数、文字边界、编译日志，并渲染所有页面逐页检查。交付 PDF、预览、可编辑源码、验证报告和仍需我补充的问题，明确自动检查与视觉检查分别完成了什么。
```

## 本地快速开始

需要 Python 3.10+ 和网络。Python 不存在时，agent 应通过已有的系统包管理器安装；具体平台处理见 [环境说明](skills/latex-resume/references/environment.md)。以下命令从仓库根目录运行：

```bash
git clone https://github.com/passionworkeer/latex-resume-skill.git
cd latex-resume-skill
python3 skills/latex-resume/scripts/setup.py
.venv/bin/python skills/latex-resume/scripts/build.py \
  --source skills/latex-resume/assets/templates/example-zh.md \
  --output output/example-zh
```

Windows PowerShell 将 `python3` 换成 `py -3`，将 `.venv/bin/python` 换成 `.venv/Scripts/python.exe`。安装脚本支持 macOS、Linux 的 ARM64 / x86_64，以及 Windows x86_64 的引擎下载；平台覆盖和实际测试结果分开记录在 [验证记录](docs/VALIDATION.md)。

`setup.py` 自动创建 `.venv/`、安装 Python 包、检查已有 Tectonic / XeLaTeX、必要时下载 Tectonic 到 `.tools/bin/`，并下载、校验和生成字体。无需全局安装字体，无需手工下载 TeX 包。首次字体生成和联网编译可能需要数分钟，后续使用缓存。脚本不修改 shell 配置、不运行远程安装脚本、不自动提权。

构建生成 `resume.pdf`、`resume.tex`、字体副本、正文对照文件、日志、逐页 PNG 和机器验证报告。**脚本通过后，agent 仍须打开所有预览检查重叠、裁切和可读性。** 不能把“编译成功”当作交付完成。

日常使用先把示例复制到 `private/resume.md` 再修改；不要往公开示例中写真实内容。Markdown 子集、编译选项和手工模板入口见 [源码格式](skills/latex-resume/references/source-format.md)。

## 安装为 skill（可选）

最简单的方式是让 agent 直接读取仓库内的 `SKILL.md`。如果使用 Codex，也可以把整个 `skills/latex-resume/` 目录复制到 `~/.codex/skills/latex-resume/`，或在可用时使用 skill 安装器指定本仓库和该子路径。已存在同名 skill 时先检查差异，避免覆盖本地修改。

只复制 `SKILL.md` 不够：脚本、模板、下载清单和参考文档都需要一起保留。安装后可以用 `$latex-resume` 调用；首次使用让 agent 选定工作目录，在该目录运行安装位置下的 `scripts/setup.py`，后续构建也从同一个工作目录执行。

## 工作流程

1. **读取和核实**：提取原简历文字，查看原始页面，明确岗位、语言、篇幅和用户优先级。扫描件用 OCR 辅助，并回看图片纠错。
2. **补充项目背景**：围绕问题、个人职责、方案取舍、结果与证据提问。信息不足时保留问题清单；不把团队成果自动归为个人成果。
3. **优化表达**：先给出有依据的改稿，突出问题、行动和结果；数字注明条件与来源，不把本地测试写成线上效果。
4. **选择或复刻版式**：默认使用本仓库模板；新参考图先抽取布局规格，再重建 LaTeX，先比较版式，再填充用户内容。
5. **生成并迭代**：正文和模板分别维护，避免只改生成的 TeX。优先删重复、调结构，再调间距；不靠无限缩小字号挤页。
6. **验证并交付**：检查文字完整性、页数、边界和字体日志；渲染所有页面并逐页查看，交付源码和与本轮文件对应的报告。

详细步骤见 [完整流程](skills/latex-resume/references/workflow.md)、[内容与访谈](skills/latex-resume/references/content-interview.md)、[PDF / 图片模板复刻](skills/latex-resume/references/reference-reconstruction.md)。PDF / 图片参考由 agent 按文档分析和复刻，`build.py` 本身只接收约定的 Markdown 格式。用户可以要求两页或其他风格；单页是自带模板的默认值，不是所有简历的硬性规则。

## 项目结构

```text
skills/latex-resume/
  SKILL.md                 agent 入口
  scripts/                 环境准备、生成、验证
  assets/templates/        可编辑 LaTeX 和虚构中英文 Markdown
  references/              工作流程、访谈、模板复刻和环境说明
examples/                  可公开分享的虚构 PDF / PNG
licenses/                  第三方许可证
private/                   用户资料与访谈笔记（Git 忽略）
output/                    用户生成结果（Git 忽略）
```

## 许可与边界

项目原创代码和文档采用 [MIT License](LICENSE)。模板沿用单栏 LaTeX 简历的设计思路，保留 [zheyuye/resume-chinese](https://github.com/zheyuye/resume-chinese) 的 [MIT 署名](licenses/resume-chinese-MIT.txt)。没有复制 CodeCV 网页代码、iconfont 或品牌素材。

[Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc) 使用 [SIL OFL 1.1](licenses/NotoSansSC-OFL.txt)，由安装脚本从固定提交下载并校验，不归入项目 MIT。Tectonic 从[官方发行版](https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0)下载；相关引擎、TeX 包和 Python 依赖保留各自许可，见 [第三方说明](THIRD_PARTY_NOTICES.md)。若替换为商业模板、字体或图片，请核对自己的使用和分享权限。

`.gitignore` 只是防止误提交的一层保护。发布自己的 fork 前仍应检查暂存文件、PDF 元数据、截图和 Git 历史。这个 skill 不会替用户证明经历真实性，也不保证招聘系统排名或录用结果。

## English

An agent skill for evidence-based resume editing, project-background interviews, editable LaTeX typesetting, and PDF/image reference reconstruction. Includes fictional Chinese and English examples, a local dependency bootstrapper, content/layout checks, and a required visual review loop. Read [SKILL.md](skills/latex-resume/SKILL.md), run `scripts/setup.py` from your workspace, then build a fictional example before working on private content.
