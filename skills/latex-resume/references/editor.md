# 本地 Markdown 编辑器

v0.3 编辑内核实际复用 MIT 许可的 ByteMD 1.21.0，前端已预打包，使用者无需 Node。编辑器适合已经确定内容、希望自己改文字并查看排版的用户。它复用 `build.py` 和验证流程，预览来自实际 PDF 的逐页 PNG。它不会自动润色、虚构经历或替用户进行内容核实，也不会把 HTML 预览当成最终 PDF。

## 启动

先运行 `scripts/setup.py` 自动安装 Python 依赖、字体和编译器，并完成一次样例构建（见 [environment.md](environment.md)），再运行：

```sh
.venv/bin/python skills/latex-resume/scripts/preview.py \
  --workspace private/editor
```

路径以仓库根目录为例；安装为 skill 后请改成实际安装位置。Windows 使用 `.venv/Scripts/python.exe`。默认端口是 8765，启动后通过系统默认外部浏览器打开页面。只监听 `127.0.0.1`，不是公网托管服务。不要把个人编辑工作区提交到仓库。

首次载入虚构中文示例；重复使用相同工作区则读取已保存的 `resume.md`。导入自己的 Markdown 时可指定：

```sh
.venv/bin/python skills/latex-resume/scripts/preview.py \
  --source private/resume.md --workspace private/editor-import --pages 1
```

`--source` 将内容复制为工作区草稿，不回写输入文件。工作区存在不同内容时会报错，避免覆盖；省略 `--source` 继续原草稿，或选择新工作区。

可选参数：

- `--pages 1`：预期页数，允许 1–20；检查不符会报错，不静默删内容或缩字。
- `--port 0`：选择空闲端口，终端会打印实际地址。也可指定固定端口。
- `--no-open`：只启动服务并打印 URL，由用户自行在外部浏览器打开。

终端需保持运行；按 Ctrl+C 停止服务。不要为停止本任务而关闭其他浏览器窗口或共享进程。

## 编辑、图标与生成

1. 直接编辑 Markdown，格式见 [source-format.md](source-format.md)。也可点击「打开 Markdown」载入本地文件。
2. 需要装饰图标时点击「插入图标」，按名称或 ID 搜索 28 个本地图标，例如 GitHub。点击图标插入 `![logo:github]`，保留旁边的文字名称；图标身份、来源和品牌使用限制见 [logos.md](logos.md)。
3. 编辑停顿 **650ms** 后默认自动保存并调用 LaTeX 排版；也可点击「重新生成」。排版可能需要数秒，首次下载字体或 TeX 资源可能更慢。
4. 可改正文、加粗与正文字号（9–12 pt，步进 0.5 pt，默认 10.5 pt）；标题和布局固定。右侧是实际 LaTeX PDF 的页面图像，不是浏览器 HTML 渲染。
5. 当前版本编译与校验成功后可分别导出 PDF、PNG、Markdown。单页 PNG 直接下载，多页打包 ZIP；仍须逐页检查重叠、裁切、间距与可读性。Markdown 导出只有正文，字号与页数不写入 Markdown。

图标通过清单 ID 解析本地 SVG，构建时转换为矢量 PDF；不运行远程图标脚本，也不从 CDN 查找缺失 ID。产品标识不能冒充公司标识，添加图标也不证明任职或技能。

## 保存与过期结果

「打开 Markdown」和输入文字先修改编辑器；默认停顿 650ms 后保存并生成。字号与预期页数保存为工作区 `editor-settings.json`，重启同一工作区可恢复。关闭页面前查看保存状态；连接中断或未完成保存时，导出 Markdown 保留当前正文。编辑器不承诺浏览器崩溃后的未保存内容恢复。

编译前会写入 `resume.md`，已有草稿备份为 `resume.previous.md`（单个上一版本，不是完整历史）。语法错误、编译失败或超时不应丢掉已写入的草稿。重新运行同一工作区可继续编辑。

每次构建使用独立 `builds/<构建ID>/`。编辑文字、字号或预期页数后，旧预览标为过期，旧 PDF / PNG 导出立即禁用；失败时可保留上次成功预览供比较，但它不代表本轮生成成功。编译过程中又修改内容时，前一快照的结果不能替代最新编辑内容。

## 排错

- **依赖未就绪：** 先完成 `setup.py` 和终端样例构建。首次字体准备或 Tectonic 资源下载可能耗时，编辑器构建有 600 秒超时。
- **语法报错：** 展开详细信息，按提示修正源码。只支持约定子集，不支持一般 Markdown 图片、HTML 或原始 TeX；未知图标 ID 也会失败。
- **页数或文字验证失败：** 检查正文和预期页数，合理精简或明确调整页数，不能跳过验证冒充成功。
- **地址被占用：** 使用 `--port 0` 或另一个空闲端口，不终止不属于本任务的进程。
- **连接断开：** 确认终端服务仍在运行；浏览器未保存修改先下载 Markdown。重新启动时保留原工作区。

页面与接口仅面向本机使用，带有 Host/Origin 校验和会话令牌检查。简历正文在浏览器与本机服务之间处理；首次依赖下载仍可能联网。该模式不提供多人协作、远程账户或公网访问隔离保证。

## 维护与分发

前端源码为仓库 `frontend/editor.js`；维护者运行 `npm ci`、`npm run build`、`npm test`。终端使用者直接运行已打包编辑器，不需要 Node。源码 ZIP 应包含 `assets/editor/bundle.js`、`bundle.css`、完整 frontend licenses 和 notices。选型与设计见仓库 `docs/LIVE-EDITOR-RESEARCH.md`、`docs/TEA-DESIGN.md`。
