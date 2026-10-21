import { Editor } from 'bytemd';
import zh from 'bytemd/locales/zh_Hans.json';
import 'bytemd/dist/index.css';
import { currentArtifact, validSettings } from './state.js';
const $ = id => document.getElementById(id);
let editor, cm, token='', value='', revision=0, saved=-1, rendered=-1, busy=false, last=null, timer, ticker, started=0, logos=[], sourceName='resume.md';
function error(message, log='') { $('error-box').hidden=false; $('error-message').textContent=message; $('error-log').textContent=log; }
function current() { return currentArtifact({revision,rendered,busy,last}); }
function status() {
  $('save-state').textContent=saved===revision?'已保存到本机':'修改待保存';
  $('preview-state').textContent=busy?`正在排版 · ${Math.floor((performance.now()-started)/1000)} 秒`:current()?'已同步':last?'预览待更新':'等待排版';
  $('export-pdf').disabled=$('export-png').disabled=!current();
  $('build-button').disabled=!token||busy;
}
function changed() { revision++; $('error-box').hidden=true; status(); clearTimeout(timer); timer=setTimeout(sync,650); }
function scale() {
 const host=$('preview-host'); const wrap=host.parentElement;
 host.style.width=$('zoom').value==='100'?'794px':'100%';
 host.style.maxWidth=$('zoom').value==='100'?'none':'794px';
 wrap.scrollLeft=0;
}
function showPages(result) {
 const fragment=document.createDocumentFragment();
 result.previews.forEach((url,i)=>{const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=url;img.alt=`LaTeX 简历第 ${i+1} 页`;caption.textContent=`第 ${i+1} 页 / 共 ${result.previews.length} 页`;figure.append(img,caption);fragment.append(figure);});
 $('preview-host').replaceChildren(fragment);$('page-count').textContent=`${result.previews.length} 页`;scale();
}
async function sync() {
 clearTimeout(timer);if(!token||busy)return;
 const settings={pages:Number($('pages').value),font_size:Number($('font-size').value)};
 if(!validSettings(settings)) {error('页数需为 1–20 的整数，字号需为 9–12 pt，步进 0.5。');return;}
 const requested=revision, snapshot=value; busy=true;rendered=-1;started=performance.now();ticker=setInterval(status,1000);$('error-box').hidden=true;status();
 try {
  const response=await fetch(snapshot.trim()?'/api/build':'/api/save',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':token},body:JSON.stringify({source:snapshot,revision:requested,...settings})});
  const result=await response.json();if(result.source_saved===true)saved=requested;
  if(!response.ok||!result.ok)throw Object.assign(new Error(result.error||'排版未通过'),{log:result.log||''});
  if(requested!==revision)return;
  if(!snapshot.trim()) {$('preview-host').replaceChildren();$('page-count').textContent='';last=null;rendered=-1;return;}
  if(!result.previews?.length||!result.pdf_url||result.revision!==requested)throw new Error('未收到对应版本的完整预览，请重新生成。');
  last=result;rendered=requested;showPages(result);
 } catch(e) {if(requested===revision)error(e.message,e.log||'');}
 finally {busy=false;clearInterval(ticker);status();if(requested!==revision)timer=setTimeout(sync,150);}
}
function download(url,name) {const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();}
$('download-source').onclick=()=>{const url=URL.createObjectURL(new Blob([value],{type:'text/markdown;charset=utf-8'}));download(url,sourceName.replace(/\.(md|markdown)$/i,'')+'.md');setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('export-pdf').onclick=()=>{if(current())download(last.pdf_url,'resume.pdf');};
$('export-png').onclick=()=>{if(current())download(last.previews.length===1?last.previews[0]+'?download=1':`/builds/${last.build_id}/previews.zip`,last.previews.length===1?'resume.png':'resume-previews.zip');};
$('build-button').onclick=sync;
$('pages').oninput=changed;$('font-size').onchange=changed;$('zoom').onchange=scale;
$('open-button').onclick=()=>$('file-input').click();
$('file-input').onchange=async event=>{const file=event.target.files[0];if(!file||!editor)return;try{if(file.size>200000)throw new Error('文件超过 200 KB，请精简后导入。');const text=await file.text();sourceName=file.name;$('source-name').textContent=sourceName;value=text;editor.$set({value});changed();}catch(e){error(e.message);}event.target.value='';};
function renderLogos() {
 const query=$('logo-search').value.toLowerCase(),fragment=document.createDocumentFragment();
 logos.filter(x=>`${x.id} ${x.name} ${(x.aliases||[]).join(' ')}`.toLowerCase().includes(query)).forEach(logo=>{const b=document.createElement('button'),img=document.createElement('img');img.src='/assets/logos/'+encodeURIComponent(logo.file);img.alt='';b.append(img,document.createTextNode(logo.name));b.onclick=()=>{if(!cm)return;const cursor=cm.getCursor(),line=cm.getLine(cursor.line),prefix=line.match(/^(?:#{1,3}|-)\s+/);cm.replaceRange(`![logo:${logo.id}] `+(line.trim()?'':'名称'),{line:cursor.line,ch:prefix?prefix[0].length:cursor.ch});cm.focus();};fragment.append(b);});
 $('logo-list').replaceChildren(fragment);
}
$('logo-search').oninput=renderLogos;
$('logo-toggle').onclick=()=>{$('logo-picker').hidden=!$('logo-picker').hidden;$('logo-toggle').setAttribute('aria-expanded',String(!$('logo-picker').hidden));};
$('bold-button').onclick=()=>{if(!cm)return;const text=cm.getSelection()||'重点内容';cm.replaceSelection(text.startsWith('**')&&text.endsWith('**')?text.slice(2,-2):`**${text}**`,'around');cm.focus();};
$('undo-button').onclick=()=>cm?.undo();$('redo-button').onclick=()=>cm?.redo();
window.addEventListener('beforeunload',e=>{if(token&&saved!==revision){e.preventDefault();e.returnValue='';}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();sync();}});
(async()=>{
 try {
  const response=await fetch('/api/session');if(!response.ok)throw new Error('无法连接本机编辑服务');const session=await response.json();
  token=session.token;value=session.source;sourceName=session.source_name;logos=session.logos||[];saved=revision;
  $('source-name').textContent=sourceName;$('pages').value=session.default_pages||1;$('font-size').value=session.font_size||10.5;
  editor=new Editor({target:$('editor-host'),props:{value,locale:zh,mode:'tab',previewDebounce:0,maxLength:200000,plugins:[{editorEffect({editor:instance}){cm=instance;}}],editorConfig:{lineWrapping:true,screenReaderLabel:'简历 Markdown 内容'},overridePreview(){}}});
  editor.$on('change',({detail})=>{if(value===detail.value)return;value=detail.value;editor.$set({value});changed();});
  for(const id of ['open-button','download-source','bold-button','undo-button','redo-button'])$(id).disabled=false;
  renderLogos();status();sync();
 }catch(e){error(e.message);$('save-state').textContent='连接失败';}
})();
