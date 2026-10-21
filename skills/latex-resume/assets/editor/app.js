'use strict';
const $ = id => document.getElementById(id);
let token = '', revision = 0, compiledRevision = -1, savedRevision = -1, failedRevision = -1, building = false, timer, logos = [], sourceName = 'resume.md';
const source = $('source'), pages = $('pages');
function updateState() {
  const current = compiledRevision === revision && failedRevision !== revision;
  $('status-dot').className = 'status-dot' + (compiledRevision < 0 ? '' : current ? ' good' : ' stale');
  $('preview-state').textContent = building ? '正在生成当前内容…' : compiledRevision < 0 ? '尚未生成' : current ? '预览与当前内容一致' : '预览已过期 · 显示上次成功结果';
  $('save-state').textContent = building ? '正在保存草稿并编译，请稍候…' : savedRevision === revision ? '当前草稿已保存到本机会话目录' : '有尚未保存的修改 · 点击生成时保存，或下载 Markdown';
  $('build-button').disabled = !token || building;
  $('build-button').firstChild.textContent = building ? '正在生成… ' : '保存并生成 PDF ';
  if (compiledRevision >= 0) $('download-pdf').textContent = current ? '下载 PDF' : '下载上次 PDF（已过期）';
}
function changed() {
  revision++;
  updateState();
  clearTimeout(timer);
  if ($('auto-render').checked) timer = setTimeout(build, 1000);
}
function showError(message, log = '') {
  $('error-message').textContent = message;
  $('error-log').textContent = log || '无额外日志';
  $('error-box').hidden = false;
}
async function build() {
  clearTimeout(timer);
  if (!token || building) return;
  const count = Number(pages.value);
  if (!Number.isInteger(count) || count < 1 || count > 20) { showError('预期页数应为 1 到 20 之间的整数。'); return; }
  const requestedRevision = revision;
  building = true;
  $('error-box').hidden = true;
  updateState();
  try {
    const response = await fetch('/api/build', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Session-Token': token }, body: JSON.stringify({ token, source: source.value, pages: count, revision: requestedRevision }) });
    const result = await response.json();
    if (result.source_saved === true) savedRevision = requestedRevision;
    if (!response.ok || !result.ok) throw Object.assign(new Error(result.error || `生成失败（HTTP ${response.status}）`), { log: result.log });
    if (requestedRevision !== revision || result.revision !== requestedRevision) return;
    if (!Array.isArray(result.previews) || !result.previews.length || !result.pdf_url) throw new Error('服务未返回完整的 PDF 预览，请重新生成。');
    const fragment = document.createDocumentFragment();
    result.previews.forEach((url, index) => {
      const figure = document.createElement('figure');
      const img = document.createElement('img');
      img.src = url; img.alt = `简历 PDF 第 ${index + 1} 页`; img.loading = index ? 'lazy' : 'eager';
      const caption = document.createElement('figcaption'); caption.textContent = `第 ${index + 1} 页 / 共 ${result.previews.length} 页`;
      figure.append(img, caption); fragment.append(figure);
    });
    $('preview-pages').replaceChildren(fragment);
    compiledRevision = requestedRevision; failedRevision = -1;
    $('page-count').textContent = `${result.previews.length} 页`;
    const link = $('download-pdf'); link.href = result.pdf_url; link.download = 'resume.pdf'; link.classList.remove('disabled'); link.setAttribute('aria-disabled', 'false');
  } catch (error) {
    if (requestedRevision === revision) { failedRevision = revision; showError(error.message || '无法连接本机服务，请检查服务是否仍在运行。', typeof error.log === 'string' ? error.log : error.log ? JSON.stringify(error.log, null, 2) : ''); }
  } finally {
    building = false; updateState();
    if (revision !== requestedRevision && $('auto-render').checked) timer = setTimeout(build, 1000);
  }
}
source.addEventListener('input', changed);
pages.addEventListener('input', changed);
$('build-button').addEventListener('click', build);
$('auto-render').addEventListener('change', () => { clearTimeout(timer); if ($('auto-render').checked && compiledRevision !== revision) timer = setTimeout(build, 1000); });
document.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); build(); } });
$('open-button').addEventListener('click', () => $('file-input').click());
$('file-input').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file || !token) return;
  try { source.value = await file.text(); sourceName = file.name; $('source-name').textContent = sourceName; changed(); } catch (error) { showError('无法读取所选 Markdown 文件。', error.message); }
  event.target.value = '';
});
$('download-source').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([source.value], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = sourceName.replace(/\.(md|markdown)$/i, '') + '.md'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
function renderLogos() {
  const query = $('logo-search').value.toLowerCase();
  const fragment = document.createDocumentFragment();
  logos.filter(logo => `${logo.id} ${logo.name} ${(logo.aliases || []).join(" ")}`.toLowerCase().includes(query)).forEach(logo => {
    const button = document.createElement('button'); button.type = 'button';
    const img = document.createElement('img'); img.alt = ''; img.src = '/assets/logos/' + encodeURIComponent(logo.file);
    const label = document.createElement('span'); label.textContent = logo.name || logo.id;
    button.append(img, label);
    button.addEventListener('click', () => {
      const cursor = source.selectionStart;
      const lineStart = source.value.lastIndexOf('\n', cursor - 1) + 1;
      const nextBreak = source.value.indexOf('\n', cursor);
      const line = source.value.slice(lineStart, nextBreak < 0 ? source.value.length : nextBreak);
      const prefix = line.match(/^(?:#{1,6}|[-*+])\s+/);
      const position = prefix ? lineStart + prefix[0].length : cursor;
      const insertion = `![logo:${logo.id}] ` + (line.trim() ? '' : '名称');
      source.setRangeText(insertion, position, position, 'end'); source.focus(); changed();
    });
    fragment.append(button);
  });
  if (!fragment.childNodes.length) { const empty = document.createElement('p'); empty.className = 'hint'; empty.textContent = '没有匹配的图标'; fragment.append(empty); }
  $('logo-list').replaceChildren(fragment);
}
$('logo-toggle').addEventListener('click', () => { const hidden = !$('logo-picker').hidden; $('logo-picker').hidden = hidden; $('logo-toggle').setAttribute('aria-expanded', String(!hidden)); if (!hidden) $('logo-search').focus(); });
$('logo-search').addEventListener('input', renderLogos);
window.addEventListener('beforeunload', event => { if (token && savedRevision !== revision) { event.preventDefault(); event.returnValue = ''; } });
(async () => {
  try {
    const response = await fetch('/api/session'); if (!response.ok) throw new Error(`连接失败（HTTP ${response.status}）`);
    const session = await response.json();
    if (!session.token || typeof session.source !== 'string') throw new Error('本机会话数据不完整。');
    token = session.token; source.value = session.source; source.disabled = false; $('open-button').disabled = false; $('download-source').disabled = false;
    sourceName = session.source_name || 'resume.md'; $('source-name').textContent = sourceName;
    pages.value = session.default_pages || 1; savedRevision = revision;
    logos = (session.logos || []).filter(logo => /^[a-zA-Z0-9_-]+$/.test(logo.id) && typeof logo.file === 'string'); renderLogos(); updateState();
  } catch (error) { source.placeholder = '未能读取草稿。请确认本机服务已启动，再刷新页面。'; showError(error.message); $('save-state').textContent = '连接失败 · 未载入草稿'; }
})();
