# v0.5 可视化编辑方案

用户希望直接修改简历上的文字，隐藏 Markdown 标记，保留 LaTeX 的版式、分页和输出。此次复用 [Tiptap Core / StarterKit 3.32.0](https://github.com/ueberdosis/tiptap)，MIT，底层为 ProseMirror；没有采用付费扩展或云服务。原 ByteMD Markdown 编辑器已移除。依赖精确锁定并生成完整第三方许可证文件。

Tiptap 提供成熟的选区、撤销/重做、加粗和输入能力。参考其官方 [TextStyle](https://tiptap.dev/docs/editor/extensions/marks/text-style) / [FontSize](https://tiptap.dev/docs/editor/extensions/functionality/fontsize) 模型，本项目定义受限字号 mark 与 logo atom、三字段经历节点，匹配实际支持的 LaTeX 格式。转换模块独立验证，避免任意 HTML 被静默丢弃。粘贴使用纯文本；未支持的导入格式明确报错，原稿保持不变。中文输入过程中不重建编辑器，组合输入未结束时推迟编译。

内容链路：可视文档 → Markdown 子集 → LaTeX → PDF → PNG 页面预览。局部字号和图标大小进入 Markdown；模板、全文字号、预期页数保存为工作区设置。左右视图不承诺像素级一致，右侧 PDF 是排版依据。

界面把高频操作压缩到三处：顶部选模板/全文字号，左侧直接编辑和格式工具栏，右上角导出 PDF。图标放入可搜索、可筛选的弹窗；PNG/原稿和页数设置作为次要操作收起。未复制内部 Tea/RUM 代码或图形资产。

构建仍使用 650ms 停顿触发，旧导出在任何内容或设置修改后失效；只允许下载与当前编辑版本一致且经过内容、页数、溢出检查的 PDF/PNG。首次字体/TeX资源下载和实际排版存在等待时间，不能描述为逐按键即时 PDF 渲染。
