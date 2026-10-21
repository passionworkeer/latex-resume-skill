# LaTeX 唯一排版来源：实时编辑开源复用调研

核对日期：2026-10-21。用户已明确：Markdown 只负责文字、字号和加粗等内容/样式输入，LaTeX 是唯一排版来源，最终 PDF 与 PNG 必须来自同一 LaTeX 编译结果。因此取消独立 HTML Viewer、HTML 简历模板与浏览器打印作为主路线；此前这类候选不满足当前要求。

## 推荐路径

复用 **ByteMD 1.21.0 的 Vanilla JS Editor**，仅承担成熟的内容编辑能力；右侧显示现有 LaTeX build API 产生的 PNG/PDF。停顿约 650ms 后自动编译，保留旧预览并明确标记“内容已修改，预览待更新”，编译完成且通过校验后更新。无需点击“编译”，但这属于 Overleaf 式自动编译预览，不是每个按键即时排版。

PDF/PNG 导出只引用当前内容与字号/页数版本 对应的成功验证结果；结果落后、编译失败或校验失败时不能导出旧文件充当当前版本。MD 可直接保存当前原文。字号和加粗映射到同一个 LaTeX 生成器，不能另写 HTML 排版模仿最终效果。

## 当前实际耗时

在仓库根目录执行一次公开虚构中文样例，不启动 UI、不读取真实简历：

```sh
/usr/bin/time -p .venv/bin/python skills/latex-resume/scripts/build.py \
  --source skills/latex-resume/assets/templates/example-zh.md \
  --output output/timing-live --pages 1
```

结果：普通 CLI 路径一次 **7.58s**。编辑器改为先用 Tectonic `--only-cached`，检测缓存缺失时再联网补齐。更新后通过 `EditorState.compile()` 测量完整保存、编译、校验与 PNG 渲染：单独运行一次 **2.83s**；与另三个示例同时构建时 **28.61s**。两次均为同一虚构中文单页、全文比对通过。另一次仅 Tectonic 引擎调用为 **1.80s**，不能当成整个预览耗时。

这些是本机单次样本，不能承诺首次下载或不同负载的性能。650ms 是开始编译前的防抖延迟；右侧展示实际 PDF 的页面，完整构建和校验结束才刷新。

## 可复用开源方案

| 方案 | 对当前要求的作用 | 中文与一致性 | 成本与结论 |
| --- | --- | --- | --- |
| ByteMD + 当前本地 LaTeX 编译 | 复用完整编辑器、CodeMirror、工具栏、中文界面；不使用其 HTML Viewer | 所有可见排版来自现有引擎；编辑侧中文 IME 要验证 | **最低，推荐**。不更换引擎、不自研编辑器，需做版本绑定与自动任务调度 |
| md-editor-v3 5.7.0 + 当前编译 | 同样可仅复用编辑器并关闭其预览 | LaTeX 仍唯一排版 | 中。需引入 Vue `^3.5.3`，本项目没有现成 Vue 应用，收益小于 ByteMD |
| SwiftLaTeX 浏览器 WASM XeTeX | 浏览器中实际运行 XeTeX，输出真实 PDF；能复用编译 API | 仍需迁移现有模板/包/中文字体和资源；README 明确缺完整 ICU 数据，locale linebreaking 可能异常 | 高。首次加载与资源下载、缓存、字体、引擎等价性、AGPL 整合都需处理，不是简单替换；目前不推荐 |
| Overleaf 自动编译模式 | 证明真实 LaTeX 自动刷新是成熟交互；每隔数秒编译并更新 PDF | 可保留真 TeX 结果，不承诺每键即时 | 借鉴交互即可。完整自托管协作服务明显超过本地简历工具范围，无需复制其服务栈 |

ByteMD 使用固定提交 `7d942bf2af0d110e0560bec06bdda1c04c8dbeb5`：实际读取 [package.json](https://github.com/bytedance/bytemd/blob/7d942bf2af0d110e0560bec06bdda1c04c8dbeb5/packages/bytemd/package.json) 确认 1.21.0、[LICENSE](https://github.com/bytedance/bytemd/blob/7d942bf2af0d110e0560bec06bdda1c04c8dbeb5/LICENSE) 确认 MIT、[Editor 源码](https://github.com/bytedance/bytemd/blob/7d942bf2af0d110e0560bec06bdda1c04c8dbeb5/packages/bytemd/src/editor.svelte) 确认 change 事件与预览选项。npm 版本可用，不假设存在 `v1.21.0` Git tag。

md-editor-v3 固定 [v5.7.0/package.json](https://github.com/imzbf/md-editor-v3/blob/v5.7.0/package.json) 与 [MIT LICENSE](https://github.com/imzbf/md-editor-v3/blob/v5.7.0/LICENSE) 已实际读取；它的 Markdown-it/HTML 预览不应用作本项目右侧排版。

SwiftLaTeX 固定提交 `87dfb950eb9c8e9dcd4ee2a3ac97fbbbacfc618a`：[README](https://github.com/SwiftLaTeX/SwiftLaTeX/blob/87dfb950eb9c8e9dcd4ee2a3ac97fbbbacfc618a/README.md)、[AGPL-3.0 LICENSE](https://github.com/SwiftLaTeX/SwiftLaTeX/blob/87dfb950eb9c8e9dcd4ee2a3ac97fbbbacfc618a/LICENSE)。源码 API 是 `loadEngine()` → `writeMemFSFile()` → `setEngineMainFile()` → `compileLaTeX()`；引擎在 worker 中运行，包资源可通过 `setTexliveEndpoint()` 指向自托管服务。README 的兼容性宣传不等于本项目中文模板已验证等价，尤其其明确说明 ICU 限制。整合前需要按实际代码边界审查 AGPL 与 TeX 资源各自许可，不能当作 MIT 组件复制。

Overleaf 的 [官方自动编译说明](https://docs.overleaf.com/getting-started/recompiling-your-project) 明确描述每隔数秒自动编译；[官方编译流程](https://www.overleaf.com/learn/how-to/How_does_Overleaf_compile_my_project) 说明采用 latexmk 自动执行必要编译轮次。这里只借鉴模式，没有引入或复制 Overleaf 源码，因此不声称已完成其固定版本许可审计。

## ByteMD npm API 接入要点

默认 `bytemd` dist 入口已编译，不需要新建 Svelte 应用，也不应为此引入 Svelte 5 runtime；该版本没有 Svelte runtime peerDependency。若 bundler 装有会按 `svelte` 字段改用源码的插件，应明确使用默认 dist 入口，避免误导到源码组件。

```js
import { Editor } from 'bytemd';
import 'bytemd/dist/index.css';
import zhHans from 'bytemd/locales/zh_Hans.json';

let value = initialMarkdown;
const editor = new Editor({
  target: document.querySelector('#resume-editor'),
  props: { value, plugins: [], mode: 'tab', locale: zhHans },
});
const unsubscribe = editor.$on('change', ({ detail }) => {
  value = detail.value;
  editor.$set({ value }); // 受控输入必须回写
  scheduleLatexBuild(value); // 业务自动编译调度，不创建 Viewer
});
// 清理：unsubscribe(); editor.$destroy();
```

使用 `mode: 'tab'` 默认编辑态，而不是 split。该版本没有公开 editorOnly 属性，可在固定版本左容器下隐藏 `.bytemd-toolbar-tab` 切换按钮；需要 DOM 验证，因为这是内部选择器。只开放现有 LaTeX 语法可支持的按钮；不添加完整 GFM 工具造成 PDF 静默丢内容。字号作为受限样式参数传入同一 LaTeX 生成器。键入期间不要重建 Editor，中文组合输入必须实测。

## 自动编译必须处理的状态

- 内容改变立即标记预览过期；650ms 停顿后排队，单个编辑会话同一时间最多一个编译，过程中继续输入只保留最新待构建版本。
- 内容与允许的排版参数一起计算版本；旧任务完成不能覆盖较新内容，校验失败不得把有误 PDF 当成成功结果。
- 右侧始终显示 LaTeX PDF 或其派生 PNG，不创建第二套 HTML 模板。PNG 由最终 PDF 生成，避免两个引擎各排一次。
- 导出按钮只在当前版本存在验证成功结果时启用；失败保留文字、最后成功预览及明确过期状态。
- 性能后续优先测编译、校验、PDF 渲染分别耗时，再决定缓存/预加载。不能为了“实时”绕过正式导出所需校验。

## 已排除的 HTML 方案

[ShowCV 固定提交](https://github.com/showlotus/ShowCV/tree/088250102fd9fdf09128ad80b486a90cd9ff8085) 的 [MIT 许可](https://github.com/showlotus/ShowCV/blob/088250102fd9fdf09128ad80b486a90cd9ff8085/LICENSE) 与 [pdfService.ts](https://github.com/showlotus/ShowCV/blob/088250102fd9fdf09128ad80b486a90cd9ff8085/src/services/pdfService.ts) 已核对：主路线是 react-to-print/iframe 浏览器打印 PDF，PNG 用 modern-screenshot `domToBlob`。它符合 HTML 简历产品，但不符合本任务 LaTeX 唯一来源，故不采用。

resume.md / markdown-resume 类 Python+Markdown+CSS+Chrome 打印方案也不采用；[所核对 resume.md 的固定 MIT LICENSE](https://github.com/honestsoul/resume.md/blob/6a9525b5cc3c85045c48f3e607f0e0cd176dfb81/LICENSE) 与 [脚本](https://github.com/honestsoul/resume.md/blob/6a9525b5cc3c85045c48f3e607f0e0cd176dfb81/resume.py) 仅作为排除证据。CodeMirror+marked 需要自行装配编辑器交互，且 marked 不负责 LaTeX；已有 ByteMD 可复用，没有必要另造编辑器。
