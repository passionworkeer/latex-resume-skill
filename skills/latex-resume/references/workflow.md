# Reproducible build and delivery

## 1. Preserve inputs and choose authority

Keep supplied originals and a timestamped snapshot of current source, layout, assets, and PDF before overwriting a draft. Use the repository's ignored private/output directories, or another explicitly private workspace. Inspect Git status and ignore rules before staging anything; the public repository should contain fictional examples and reusable machinery.

For the bundled flow, Markdown is content authority and the template/generator is layout authority. Generated TeX is useful for diagnosis; make durable fixes in its upstream source. A custom reconstruction may instead use hand-authored TeX as authority. Record that choice so a later build cannot overwrite it. Preserve related font files and licenses.

## 2. Prepare dependencies

Run from the repository root:

```sh
python3 skills/latex-resume/scripts/setup.py --check
python3 skills/latex-resume/scripts/setup.py
```

The normal setup installs missing Python dependencies in `.venv`, supplies fonts, and installs a user-local Tectonic compiler when needed. Reuse existing healthy tools. `--check` diagnoses availability without installing. If Python or system packages are missing, follow [environment.md](environment.md) to install them within the environment's permissions; do not invoke elevated privileges without the required approval. Read the actual script diagnostics and `--help` for platform limitations.

A compiler's first run may download its TeX bundle/packages. If network or installation fails, report the actual missing item and preserve the editable sources. Do not call a stale PDF a successful build. Do not weaken verification to bypass missing fonts or unsupported characters.

## 3. Generate and compile

For the fictional bundled example:

```sh
.venv/bin/python skills/latex-resume/scripts/build.py \
  --source skills/latex-resume/assets/templates/example-zh.md \
  --output output/example-zh
```

For personal work, use a private source path and output directory. Inspect the supported source format and template before adding structures; a purpose-built renderer is not a general Markdown engine. If new syntax is needed, update generation and expected-content handling together, then verify real output. Never delete unsupported content just to make compilation pass.

Use a fresh or clearly identified output directory. Confirm process success and current file timestamps. A failed compiler can leave an older PDF in place. Compile custom TeX with the selected engine and asset paths, keep its log, and disable shell escape.

## 4. Check content and diagnostics

```sh
.venv/bin/python skills/latex-resume/scripts/verify.py \
  --pdf output/example-zh/resume.pdf \
  --expected output/example-zh/expected-text.txt \
  --log output/example-zh/resume.log --pages 1
```

Expected content must come from the authoritative source, not be copied from the PDF being tested. Review verifier results and extraction differences. Whitespace normalization may be reasonable; omitted wording, changed digits, lost characters, or incorrect reading order need investigation. Keep punctuation and normalization rules visible rather than broadening them until any output passes.

Check the log for overfull boxes, missing characters, font substitutions, and compile errors. Repair overflow and missing glyphs. Investigate underfull boxes and other warnings in context: some are visually harmless. A successful exit alone does not prove that all text is visible or correctly aligned. Text equality does not establish factual accuracy.

## 5. Render and inspect every page

Use the build/verifier's preview outputs when available, or render the complete PDF with Poppler:

```sh
pdftoppm -scale-to 1800 -png output/example-zh/resume.pdf output/example-zh/page
```

A Python PDF renderer such as PyMuPDF or pypdfium2 is a valid alternative when available. Do not use a first-page-only rendering option until the page count is confirmed. Open the actual generated images with the environment's image-viewing tool; creating images without looking at them is not visual review.

Inspect titles and dates, contact lines, glyphs, icon baselines, list indentation, overlap, clipping, long English terms, page boundaries, and top/bottom whitespace. For reference reproduction, compare all corresponding pages. After the final correction, regenerate, rerun checks, and inspect the final images again.

When compacting a resume, first remove authorized repetition, then tune local wrapping and entry widths, and only then adjust global spacing. Preserve legible type and margins. Short continuation lines can indicate awkward wrapping; a half-line fill heuristic can help compact single-column designs but is advisory, not a universal content gate. Do not invent claims or add filler solely to occupy whitespace.

## 6. Deliver the editable result

Return clickable paths to the PDF, page previews, authoritative content, editable layout/TeX, and any needed assets or build instructions. Identify which source to edit for content versus style. Retain a concise private change record with factual sources and limitations, language synchronization status, page count, content/log checks, and visual-review result. Hashes can bind a verification record to exact source and PDF bytes when useful.

State separately what was verified mechanically, what was visually inspected, and what facts still await user input. Do not claim visual completion when no image viewer was available. Local drafting does not authorize a website deployment, public upload, or distribution of a person's resume; perform publication only on an explicit request.
