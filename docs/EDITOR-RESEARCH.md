# Manual editor research

Reviewed on 2026-10-21. Goal: edit the existing small Markdown format manually, preview its actual typeset result, and download a regenerated PDF. The existing Python → LaTeX → Tectonic/XeLaTeX → verification pipeline remains the source of truth.

## Primary sources and licenses

The following three public projects were inspected through their README, build/package files, and the actual license text. Links are pinned to the observed branch heads so future changes do not silently change this assessment.

| Project | Observed architecture and useful pattern | License evidence | Decision |
| --- | --- | --- | --- |
| [Reactive Resume](https://github.com/reactive-resume/reactive-resume/tree/677b18784c953d26cd4876531441f8cf25d2ef62) | Its [package manifest](https://github.com/reactive-resume/reactive-resume/blob/677b18784c953d26cd4876531441f8cf25d2ef62/package.json) defines pnpm workspaces, Turbo orchestration, server/web/mobile commands and database tasks. The [README](https://github.com/reactive-resume/reactive-resume/blob/677b18784c953d26cd4876531441f8cf25d2ef62/README.md) describes an editor with a live PDF preview and multiple export formats. | [LICENSE](https://github.com/reactive-resume/reactive-resume/blob/677b18784c953d26cd4876531441f8cf25d2ef62/LICENSE): MIT, copyright Amruth Pillai. MIT permits reuse subject to preserving its notice and permission text in copies or substantial portions. | Learn from keeping editing and output visible together. Importing the whole application would add unrelated runtime and data-model complexity. |
| [OpenResume](https://github.com/xitanggg/open-resume/tree/4f8255a2c763479837f69f1dccf2a3338730cd79) | [package.json](https://github.com/xitanggg/open-resume/blob/4f8255a2c763479837f69f1dccf2a3338730cd79/package.json) uses Next.js, React, Redux Toolkit and react-pdf. Its [README](https://github.com/xitanggg/open-resume/blob/4f8255a2c763479837f69f1dccf2a3338730cd79/README.md) describes immediate PDF updates and browser-local resume handling. | [LICENSE](https://github.com/xitanggg/open-resume/blob/4f8255a2c763479837f69f1dccf2a3338730cd79/LICENSE): GNU Affero General Public License version 3. This is copyleft, including a source-offer requirement for remote users of modified covered software under section 13; it is not a permissive MIT grant. | Take the general edit/preview interaction as inspiration. Do not copy its code, styles or assets into this MIT project as if permissively licensed. Adopting covered code would require a separate license-compliance decision. |
| [The Markdown Resume / pandoc_resume](https://github.com/mszep/pandoc_resume/tree/b5abc55e0cbe54b132069c9c487c81d6f10b8679) | The [README](https://github.com/mszep/pandoc_resume/blob/b5abc55e0cbe54b132069c9c487c81d6f10b8679/README.md) starts with editing a Markdown file. Its [Makefile](https://github.com/mszep/pandoc_resume/blob/b5abc55e0cbe54b132069c9c487c81d6f10b8679/Makefile) generates PDF through Pandoc and ConTeXt, plus HTML and other formats. | [LICENSE](https://github.com/mszep/pandoc_resume/blob/b5abc55e0cbe54b132069c9c487c81d6f10b8679/LICENSE): MIT, copyright Mark Szepieniec. Preserve its notice if copying substantial material; inspect any selected file's own notices too. | Closest workflow fit: editable text stays portable and can be rebuilt. Keep this repository's current compiler rather than adding Pandoc/ConTeXt and another template stack. |

These are source inspections, not a runtime evaluation of the three hosted products. Dependency and asset licenses remain distinct from a repository's top-level license. Reactive Resume's former `AmruthPillai/Reactive-Resume` URL currently redirects to the organization repository above.

## Smallest practical adaptation

Add a local Python HTTP wrapper and a small original HTML/CSS/JavaScript page, with no frontend build tool. A textarea is sufficient for this deliberately limited Markdown grammar. Show a compact syntax example for `# Name`, `## Section`, `### Title | Role | Date`, bullets, bold and links; avoid implying that arbitrary Markdown is supported.

Use an explicit **Generate PDF** action first. A compiler invocation can be slower than a keystroke, and an explicit action makes saved text, pending changes and the currently previewed output understandable. Split the page into editing and preview panes on desktop, and stack them on narrow screens. Reuse `build.py` and its `verify.py` invocation; show its generated page images as the preview and offer its actual PDF for download. An HTML approximation would hide line wrapping, page count and font problems.

Represent pending edits, building, verified success and failure clearly. Every successful preview/download must refer to the same submitted text snapshot. If text changes after success, mark the result as needing regeneration. On failure, display useful diagnostics and do not offer an old PDF as the new result. Existing builder output invalidation makes temporary per-build output directories a sensible wrapper boundary.

Bind to loopback and open the user's default external browser. Preserve Markdown import/export or local-file persistence so the user's content remains editable outside the page. Prefer a self-contained local page without remote scripts, analytics, account setup or a database. First-time font/TeX resource setup can still require network access; describe that separately from handling resume text.

## Copied versus inspired

This research adds documentation only. No source code, styles, templates, icons, screenshots or other assets from these three projects were copied. The proposed textarea and side-by-side preview are independently implementable general interaction patterns. Existing third-party template/font notices in this repository continue to apply separately.

Any later code reuse must record the exact upstream file and commit, keep required notices, inspect file-specific terms and update `THIRD_PARTY_NOTICES.md`. User permission to reuse code does not replace upstream license obligations. The recommended implementation needs no upstream code copying.

## UX acceptance flows

1. **First use:** launch the editor with a synthetic example, see a short explanation and editable text, generate a verified PDF, inspect the actual page preview, then download and open that same PDF.
2. **Manual edit:** replace an experience bullet with unique Chinese text and punctuation, regenerate, and confirm that both the rendered page and extracted PDF text contain the change. The source remains editable Markdown.
3. **Unsaved/pending state:** change text after a successful build; the UI identifies the preview as older until regeneration completes. Saving/downloading Markdown preserves the complete latest edit.
4. **Invalid syntax:** submit an unsupported or malformed heading/span; retain the editor contents, show the source diagnostic, and prevent a previous result from appearing as a successful new build. Correct the text and recover without restarting.
5. **Overflow:** add enough synthetic content to exceed the configured page limit; show the verification failure and a useful action to shorten content or change the explicit page target. Never silently shrink fonts or drop text to claim success.
6. **Build lifecycle:** repeated clicks or edits during compilation cannot associate a PDF with the wrong text. A failed or older request cannot overwrite a newer successful result.
7. **Portability:** export Markdown, close/reopen the editor, import it, regenerate, and confirm the intended text survives. Narrow screens keep edit, generate, diagnostics and download controls reachable.
8. **Local boundary:** inspect network requests during editing/generation; resume contents stay on loopback, while documented first-run dependency downloads are handled by setup. Stop the editor cleanly without touching other browser tabs or processes.
