# 源文件与命令

## 默认 Markdown 子集

这是一种有意简化的输入格式，不是通用 Markdown 转换器。示例见 `assets/templates/example-zh.md` 和 `example-en.md`。

```markdown
# 示例姓名
后端开发 | example@example.com | [作品集](https://example.com)

## 教育经历
### 示例大学 | 软件工程本科 | 2021.09 - 2025.06
相关课程与已核实的教育信息。

## 工作经历
### 示例科技 | 后端开发实习生 | 2024.06 - 2024.09
- **问题与贡献：** 根据本人实际参与内容填写，不照搬示例经历。
- **验证结果：** 有测量条件和来源时再写数字。
```

- 必须以唯一的 `# 姓名` 开始；节标题前的普通文本作为居中联系方式。
- `## 节标题`；`### 机构或项目 | 职责或角色 | 日期` 恰好三列，用 ASCII `|` 分隔。
- `- 要点`；一行一个普通段落；空行用于源码可读性。
- 支持 `**加粗**` 和 `[文字](https://example.com)`，不支持嵌套加粗/链接。链接只允许 HTTP(S)，邮箱可先写纯文本。
- 只把链接的可见标签计入正文对照；PDF 链接目标需另行检查。
- 支持本地图标的特殊内联语法 `![logo:github]`，例如 `### ![logo:github] 示例开源项目 | 贡献者 | 2025.01 - 2025.03`。它是装饰图标，必须保留同一行的可见文字，不能用图标组成空文本行；图标不计入正文对照。ID 仅可来自本地清单，未知 ID 会报错。名称、来源和许可边界见 [logos.md](logos.md)。
- 不支持一般 Markdown 图片（如 `![描述](URL)`）、HTML、表格、代码、嵌套列表或原始 TeX。脚本遇到不支持的语法会报行号，不静默丢弃。
- 所有文本字符做 TeX 转义，输入中的反斜杠不会变成可执行命令。
- 默认模板使用同一字体和字号支持中英文；英文示例是独立虚构内容，不会自动翻译中文。

内容源是 Markdown；样式源是 `assets/templates/resume.tex`。生成的 `output/.../resume.tex` 供查看、交付或作为新的自定义模板起点，常规改稿仍应回到 Markdown 和样式源。

## 本地实时编辑

运行 `scripts/preview.py --workspace private/editor`，可在系统默认外部浏览器通过已打包的 ByteMD 1.21.0 编辑此格式、搜索插入图标，默认停顿 650ms 后自动调用 LaTeX 生成实际 PDF/逐页 PNG。编译可能需数秒，首次资源下载更慢；不使用浏览器 HTML 排版。使用 [editor.md](editor.md) 中的命令和保存规则。

编辑器仅开放正文、加粗与正文字号（9–12 pt，步进 0.5 pt，默认 10.5 pt）；标题样式与布局固定。字号和预期页数持久保存到工作区 `editor-settings.json`，导出 Markdown 只含正文，不含字体和页数设置。当前版本校验成功才可导出 PDF / PNG，编辑后旧产物过期并禁用；单页 PNG 直接下载，多页 PNG 以 ZIP 下载。

## 构建

在工作目录中运行安装位置下的脚本：

```sh
.venv/bin/python skills/latex-resume/scripts/build.py \
  --source private/resume.md --output output/resume --pages 1
```

参数：

- `--engine auto|tectonic|xelatex`：优先本地 `.tools/bin/tectonic`，然后 PATH；自动模式优先 Tectonic。
- `--pages N`：期望页数，默认 1；页数不符会失败，不会自动删除内容。
- `--bundle URL_OR_PATH`：Tectonic 资源 bundle，默认 `https://data1b.fullyjustified.net/tlextras-2022.0r0.tar`，沿用已验证流程。可指定可信本地文件；XeLaTeX 忽略此项。

输出包括 `resume.pdf`、`resume.tex`、`fonts/` 和许可、`expected-text.txt`、`resume.log`、`build.log`、`verification.json`、提取文本与 `preview-*.png`；使用图标时另有 `logos/`，包含用到的 SVG、转换后的矢量 PDF、来源清单及上游许可/免责声明。生成目录应独立，不得与原稿所在目录相同或放进已安装 skill 中。机器检查失败返回非零状态；报告中的 `visual_status` 始终待人工/agent 看图确认，不伪造视觉 PASS。

## 独立、自定义模板验证

复刻新模板时可以手写独立 `custom.tex`，保留该文件作为样式和内容的源头。先从用户的原稿独立整理 `expected.txt`，不要从最终 PDF 反向生成对照答案。

```sh
tectonic --untrusted --keep-logs custom.tex
.venv/bin/python skills/latex-resume/scripts/verify.py \
  --pdf private/custom.pdf --expected private/expected.txt \
  --log private/custom.log --pages 1 \
  --report output/custom-verification.json --render output/custom-preview
```

在 `custom.tex` 所在目录执行编译，并把验证路径调整为实际位置。也可用 XeLaTeX 的 `-no-shell-escape -halt-on-error`。字体必须随源码携带并正确引用。

`--source` 可以替代 `--expected`，但仅适用于上述 Markdown 子集。默认正文比较使用 PDF 内容流中的字符顺序，忽略空白和常见列表圆点，不忽略数字或标点。如果多栏自定义模板的内容流顺序与预期阅读顺序不同，先检查提取顺序并改进模板的文本流；必要时为该模板增加可审计的按区域比较，不能简单放宽为“词都出现过”。

未传 `--log` 时只能完成部分机器检查，整体不会通过且退出非零；交付要求必须检查本次编译日志。指定不存在或空的日志会失败。边界检查针对纸张边界，并不能自动发现所有相互重叠、页内裁切或视觉间距问题；始终逐页看图。
