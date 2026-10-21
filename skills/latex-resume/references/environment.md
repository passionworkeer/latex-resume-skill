# 环境准备和自动补齐

目标是 agent 自动把缺失的依赖装好，再继续生成，而不是只给用户一串安装建议。遵守当前运行环境的网络、安装与提权权限；普通项目内安装直接执行。只有确实被权限或网络阻止时才报告具体阻塞。

## 首选路径

需要 Python 3.10+。进入自己的工作目录，运行 `<skill>/scripts/setup.py`；仓库使用方式是：

```sh
python3 skills/latex-resume/scripts/setup.py
python3 skills/latex-resume/scripts/setup.py --check
```

安装内容：

- `.venv/`：固定直接版本的 pdfplumber、PyMuPDF、fontTools 及其依赖。间接依赖由 pip 解析，未声称完全锁定整个软件供应链。
- `.tools/bin/tectonic`：已有 Tectonic 或 XeLaTeX 时复用，否则下载固定官方发行版。支持 macOS/Linux x86_64、ARM64，Windows x86_64。
- `<skill>/assets/fonts/`：从 Google Fonts 固定提交下载 Noto Sans SC 可变字体和 OFL，校验 SHA-256 后生成完整字库的 Regular/Bold。为共享外观的标点分配独立字形身份，修复中点、列表圆点与连字符的 Unicode 提取歧义，同时保留原字符覆盖。字体和许可复制到每次构建结果。完整中文字库首次生成可能需要数分钟，后续使用缓存。
- `.cache/`：下载缓存。重复执行复用校验通过的文件；字体成品也记录哈希。

下载 URL 和 SHA-256 位于 `scripts/downloads.json`。默认不安装全局字体，不执行 `curl | sh`，不修改 PATH，不运行 sudo。引擎首次编译还会下载 TeX bundle 中需要的包；离线机器应预先联网构建一次并保留缓存。

`--workspace /path` 可指定运行时目录。之后应 `cd /path` 再构建，让构建器找到 `.tools/bin`。字体存放在 skill 目录中，因此该目录须可写；只读安装可把整个 skill 复制到可写的工作目录再执行。

## 缺少 Python、venv 或包管理器

Agent 先检测现有工具，按本机平台采取最小安装动作：

| 环境 | 已有包管理器时的处理 |
| --- | --- |
| macOS | 检测 `python3`；缺少时运行已有 Homebrew 的 `brew install python`。没有 Homebrew 时优先使用 agent 已有 Python runtime，或按 Python 官方安装指引安装；不静默执行远程 shell 安装器。 |
| Debian / Ubuntu | 在已获权限范围内安装 `python3 python3-venv python3-pip`。使用 apt-get 需要管理员权限时，遵守当前 agent 的审批机制；不得绕过。 |
| Windows | 检测 `py -3` 或 `python`；缺少时可用已有 winget 安装 Python 官方包，例如 `Python.Python.3.12`。用 `.venv/Scripts/python.exe` 执行构建。 |
| 其他 Linux / CPU | 用该发行版包管理器安装 Python 和 Tectonic / XeLaTeX；没有预编译下载时明确说明平台，而不是循环尝试错误二进制。 |

Python 官方入口：https://www.python.org/downloads/ 。系统包操作只在实际需要时执行；不要无目的升级整机环境。

## 渲染与 OCR

构建脚本优先使用已有 Poppler；没有时用 Python 包 PyMuPDF 生成所有页面的 PNG，无需额外安装 Poppler。参考 PDF 可用 pdfplumber 提取文字、PyMuPDF 渲染。如果用户给扫描 PDF 或 PNG，优先使用 agent 图像能力；必要时自动安装 Tesseract 和相应语言包（macOS `tesseract` / `tesseract-lang`，Ubuntu `tesseract-ocr` / `tesseract-ocr-chi-sim`）。OCR 仅作为转录草稿，必须与图片核对。没有 OCR 工具不代表无法进行视觉版式分析。

## 故障处理

- 网络失败：指出失败的 URL/主机、错误及已经完成的步骤；使用用户配置的代理，重试一次后定位原因。不关闭 TLS 校验、不换成来源不明的镜像。
- Tectonic bundle 下载失败：检查网络和缓存；可用 `--bundle` 指定可信本地 bundle，或使用已有完整 XeLaTeX。不要把旧 PDF 当作新编译成功。
- XeLaTeX 缺包：从发行版/TeX Live 的包管理器补齐 `fontspec xeCJK geometry xcolor hyperref titlesec enumitem` 等日志明确要求的包；常见 Linux 环境需 `texlive-xetex texlive-lang-chinese texlive-latex-extra`。
- 缺字：确认字体覆盖用户语言。Noto Sans SC 是本模板默认字体，不覆盖所有脚本和 emoji；按需要选用合法字体、更新模板并重新检查提取和渲染。
- 安装或编译失败时明确失败，不把说明文档代替交付物。确需用户提供权限/材料时，只请求那项具体缺失信息。
