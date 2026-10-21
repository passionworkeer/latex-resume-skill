# 可切换 LaTeX 模板

三套模板接收同一个受限 Markdown 格式。切换不会重写经历、移动文字或推断内容类型；标题、边距、栏目布局等由模板定义，文字大小和粗体仍由用户控制。

| ID | 名称 | 布局与来源 |
| --- | --- | --- |
| classic | 经典单栏 | 原有紧凑单栏，保留 resume-chinese 的 MIT 署名 |
| minimal | 简洁单栏 | 适配 sb2nov/resume 的 MIT 单栏设计，保留标题横线与留白 |
| two-column | 彩色双栏 | 适配 jankapunkt/latexcv 的 MIT 双栏设计，正文按源顺序流入左右栏 |

具体固定提交、改动和完整许可证随 `assets/templates/` 分发。新增模板统一使用 Noto Sans SC 字体与现有图标/字号宏，未引入上游示例人物资料、照片或商业字体。它们是兼容当前内容格式的适配版，不声称逐像素复刻原项目。

## 使用

编辑器点击「选择模板」，查看真实 LaTeX 缩略图后选择；等待新预览完成，再导出 PDF 或 PNG。命令行从项目根目录运行：

```sh
.venv/bin/python skills/latex-resume/scripts/build.py \
  --source private/resume.md --output output/resume-minimal \
  --template minimal --font-size 10.5 --pages 1
```

不同排版会改变换行和页数。内容过长时，调整内容或预期页数，不要把失败或旧模板的输出作为新版交付。双栏不等于所有招聘系统都能正确读取；需要兼容特定系统时，先使用单栏并检查文本提取。

## 添加模板

先核对源码和资产许可，再提供相同的 LaTeX 宏接口并注册到 `scripts/templates.py`。生成器只接受注册 ID，不接收外部路径。对同一中英文内容实际编译，保留正文比对、日志和逐页视觉检查。缩略图放 `assets/templates/thumbnails/<id>.png`，仅使用公开虚构内容。新模板需要在 CI 中加入构建覆盖。
