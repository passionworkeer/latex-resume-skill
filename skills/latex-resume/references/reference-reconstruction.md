# Reconstruct a PDF or image reference

## Inspect before choosing a template

Save the unmodified reference privately. Render all PDF pages or inspect the original PNG at adequate resolution. Extract PDF text and font information when available, but use the visible page as the layout reference. Image-only content or OCR needs manual review of names, dates, punctuation, and numbers; do not silently guess unreadable text.

Record the layout properties that matter:

- Page dimensions and count, margins, columns, reading order, and section placement.
- Body font family/weight, approximate size and leading, heading hierarchy, colors, and rules.
- Entry-title structure, date alignment, list indentation, paragraph spacing, and contact-line behavior.
- Icons, logos, separators, and their baselines; whether reusable source assets are supplied.

For a faithful recreation, preserve visible content unless editing was also requested. If exact fonts or assets are unavailable, choose an appropriate licensed substitute and report the visible difference. Do not remove watermarks from reference assets or present a reconstructed PDF as an original export.

## Build editable layout

Choose the simplest LaTeX structure that reproduces the reference. Use named macros and explicit style parameters for repeated entries, headings, dates, and bullets. Keep content separate from style where practical. For substantial layout differences, create a custom template or authoritative hand-authored TeX rather than forcing the bundled Markdown renderer to emulate unsupported constructs.

Use real text, not a full-page screenshot embedded in PDF. Prefer local licensed fonts and vector icons; preserve font/asset licenses and source attribution. Avoid hardcoded macros that depend on a specific fictional company or project name. Escape text input correctly and keep shell escape disabled.

Use measured dimensions rather than repeated spaces for alignment. Allow long titles and dates to coexist without overlap. Protect only short phrases that genuinely need to stay together; a large unbreakable box can create overflow elsewhere. For columns, verify that extracted PDF text has useful reading order as well as visual fidelity.

## Compare and refine

Render reference and candidate at the same dimensions. Inspect side by side; an overlay or difference image can help locate shifted baselines, margins, and section boundaries, but text changes make pixel differences noisy. Compare hierarchy and readable output, not just total page height.

Fix the highest-impact mismatches first: page geometry, columns, typography, repeated entry structure, then local line breaks and decorative details. Recompile and recheck after each meaningful layout change. Do not shrink text continuously to force a page count. If content cannot fit readably, trim only authorized redundancies or explain the specific tradeoff.

Derive `expected-text.txt` from the approved source/transcription, independently of the PDF extraction. Use the verifier on custom builds as well:

```sh
.venv/bin/python skills/latex-resume/scripts/verify.py \
  --pdf output/custom/resume.pdf \
  --expected output/custom/expected-text.txt \
  --log output/custom/resume.log --pages 1
```

Set the page count to the user's actual target. Read the build workflow for rendering and final delivery. State any remaining font, icon, line-break, or geometry differences plainly; claim close reproduction only after actual comparison.
