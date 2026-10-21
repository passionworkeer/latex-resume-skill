# Local SVG logo catalogue

The skill bundles 28 unchanged, monochrome SVG files from [Simple Icons](https://github.com/simple-icons/simple-icons). The catalogue lives in `assets/logos/manifest.json`; builds read local files and require no runtime network access. Each icon has a stable `id`, display `name`, relative `file`, pinned GitHub `source`, `sha256`, `license`, `individual_license`, `brand_url`, optional `guidelines_url`, and suggested `color`. The SVG itself remains upstream black; the suggested color is metadata, not an instruction to recolor a restricted brand mark.

The upstream snapshot is package 16.35.0, commit [`c71c69e3a27e4436936b831c72643e6513b9f49b`](https://github.com/simple-icons/simple-icons/tree/c71c69e3a27e4436936b831c72643e6513b9f49b), retrieved 2026-10-21. This is a pinned snapshot, not a promise of the latest package release. Local files contain only `svg`, `title`, and `path` elements; no scripts, event handlers, foreign objects, external references, fonts, or embedded images.

## Rights and attribution

Preserve `LICENSE.simple-icons.md` and `DISCLAIMER.simple-icons.md` when redistributing the catalogue. The upstream collection is [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/c71c69e3a27e4436936b831c72643e6513b9f49b/LICENSE.md), but its [disclaimer](https://github.com/simple-icons/simple-icons/blob/c71c69e3a27e4436936b831c72643e6513b9f49b/DISCLAIMER.md) explicitly distinguishes the collection license from rights in individual marks. These selected upstream records do not declare separate icon licenses: `individual_license: null` means undeclared. The catalogue does not claim an unconditional brand-owner redistribution grant for each underlying mark.

Company names and marks remain the property of their respective owners. Copyright licensing does not grant trademark rights or imply endorsement. Use marks only to identify real, supported experience or technology use, and check the linked brand guidelines for the intended context before public distribution. Do not turn an employer logo into the resume skill's own identity or imply affiliation with this project. A text-only company name is always available when rights or context are uncertain.

Brand terms can be narrower than a general icon collection license. For example, [Kuaishou's official material library](https://www.kuaishou.com/official/material-lib) conditions its materials on promoting Kuaishou products, source attribution, and preserving the complete image and proportions; that is not blanket permission for every resume or catalogue use. [GitHub's current brand toolkit](https://brand.github.com/foundations/logo) likewise specifies contextual logo use. Check the brand's own current rules rather than inferring permission from a download button or this catalogue.

## Available IDs

| Scope | IDs |
| --- | --- |
| Chinese companies and services | `alibabacloud`, `alibabadotcom`, `baidu`, `bilibili`, `bytedance`, `huawei`, `kuaishou`, `lenovo`, `meituan`, `xiaomi` |
| Explicit product marks | `neteasecloudmusic`, `qq`, `tencenthy`, `wechat` |
| Global companies and developer tools | `anthropic`, `apple`, `cloudflare`, `docker`, `github`, `gitlab`, `google`, `intel`, `meta`, `nvidia`, `redhat`, `samsung`, `sap`, `sony` |

`Tencent Hy`, `QQ`, and `WeChat` are distinct marks and must not be relabeled as Tencent's corporate logo. `NetEase Cloud Music` must not be relabeled as the NetEase corporate mark. Likewise `Alibaba.com` and `Alibaba Cloud` identify their respective brands, not a generic Alibaba Group corporate logo. The pinned upstream does not contain corporate `tencent` or `netease` entries. No private CodeCV assets were copied. Microsoft, Amazon, OpenAI, and other absent names have no implied fallback or legacy asset.

## Using and extending

Use a manifest ID supported by the generator/editor, for example `![logo:bytedance]` in a company heading. Keep the written company name alongside the mark for accessibility and PDF text extraction. A renderer should resolve IDs exclusively through this manifest, keep file paths inside the catalogue, preserve aspect ratio, and fail clearly for unknown IDs. Rendering syntax is implemented by the generator; this document is the asset/provenance reference.

For a missing brand, first look for current official brand resources and explicit redistribution and use terms. A GitHub repository's license must actually cover the artwork; a repository-wide MIT badge or a copied logo alone does not establish brand-owner permission. Check per-icon exceptions and removal history. Do not recover a removed logo from old releases merely to bypass the current upstream policy. Prefer a separately supplied, authorized local SVG or a text-only heading when rights are unclear. User-supplied assets stay in that user's project unless redistribution authorization is also supplied.

To update this catalogue, pin a new upstream commit, preserve its applicable license/disclaimer, inspect each selected metadata record and current brand rules, copy the SVG bytes unchanged, update SHA-256 values, and revalidate the SVG allowlist. Document provenance rather than downloading assets during resume builds. Do not silently fetch an unknown ID from a CDN.

## Chinese university logos (optional local download)

The public `university_sources` directory in `assets/logos/manifest.json` records 20 Chinese schools, including BUPT, PKU, THU, FDU, SJTU, ZJU, USTC, NJU, HIT, XJTU, WHU, HUST, BNU, RUC, NKU, TJU, SCU, SYSU, XDU and SZU. Each record has an official website/VIS lead, a pinned GitHub SVG URL and SHA-256, plus a separate rights status. University artwork is not bundled in Git. The public directory is discovery metadata; builds never download artwork.

Run explicitly from the repository root:

```sh
.venv/bin/python skills/latex-resume/scripts/fetch_school_logos.py --school bupt
.venv/bin/python skills/latex-resume/scripts/fetch_school_logos.py --all
```

The downloader checks the pinned hash and existing SVG allowlist, then stores permitted SVG structures in ignored `assets/logos/local/`, with a local manifest preserving source, source/output hashes, transformations and rights notices. It can expand plain presentation style declarations into equivalent attributes without changing paths or colors; unsupported CSS, DTDs, links, active content and unsupported elements remain rejected. `--all` reports rejected candidates individually. Local entries appear in the editor and support headings such as `![logo:bupt] 北京邮电大学`; keeping the written school name preserves accessibility and text extraction. No private resume is inspected by the downloader.

[BUPT’s official VIS](https://vi.bupt.edu.cn/) and [校徽规范](https://vi.bupt.edu.cn/jcxt/xhgf.htm) specify artwork, colors, clear space, backgrounds and prohibited forms. The optional BUPT SVG comes from [Magicdover/China-Universities-2026 at commit 419bdc7ce6956fc88c2b70b3979f170b6666f111](https://github.com/Magicdover/China-Universities-2026/tree/419bdc7ce6956fc88c2b70b3979f170b6666f111/assets/logos-new); the source bytes and converted attributes are recorded locally. This is a third-party vector rendition, not a claim of an official university-issued file. Its README’s MIT statement is not treated as a school-owner artwork or trademark grant. No broad redistribution grant was verified; use the local asset under the institution’s rules, obtain authorization for the intended context where required, and do not imply endorsement. Local download authorization does not permit publishing these assets with the skill.

Other investigated GitHub leads are [cnlogo](https://github.com/yuxtech/cnlogo) (real school vector TikZ; its [pinned license](https://github.com/yuxtech/cnlogo/blob/cdf5ece24f2a866f6f811880b0a477cb54371ee3/LICENSE) excludes logos), [china_school_badge](https://github.com/lovefc/china_school_badge) (Apache badge plus additional README restrictions), and [university_logos](https://github.com/RoboMaster/university_logos) (school copyright retained). None establishes an unrestricted school-owner grant. [This VIS index](https://github.com/wanzhenchn/Visual_Identity_System_Chinese_University) helps find official materials; only BUPT’s specific VIS endpoint was verified live in this review. The local software’s MIT license does not relicense linked university marks.

Delivered resume output includes any locally used SVG/PDF and `SOURCES.json` for the user’s private use. Check the applicable institution rules before publishing or sharing that output; keep downloaded local artwork out of the public skill repository.
