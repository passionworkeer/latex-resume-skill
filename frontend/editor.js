import { createResumeEditor } from './rich-editor.js';
import '../skills/latex-resume/assets/editor/styles.css';
import { currentArtifact, validSettings } from './state.js';
const $ = id => document.getElementById(id);
let editor, token='', value='', revision=0, saved=-1, rendered=-1, busy=false, last=null, timer, ticker, started=0, logos=[], templates=[], templateId='classic', sourceName='resume.md';
function error(message, log='') { $('error-box').hidden=false; $('error-message').textContent=message; $('error-log').textContent=log; }
function current() { return currentArtifact({revision,rendered,busy,last,templateId}); }
function status() {
 $('save-state').textContent=saved===revision?'已保存':'正在保存…';
 $('preview-state').textContent=busy?`正在更新 · ${Math.floor((performance.now()-started)/1000)} 秒`:current()?'已同步':last?'等待更新':'准备预览';
 $('export-pdf').disabled=$('export-png').disabled=!current();$('build-button').disabled=!token||busy;
}
function changed() { revision++;$('error-box').hidden=true;status();clearTimeout(timer);timer=setTimeout(sync,650); }
function applyPaperStyle() { $('editor-host').dataset.template=templateId;$('editor-host').style.setProperty('--body-size',$('font-size').value+'pt'); }
function scale() {const host=$('preview-host');host.style.width=$('zoom').value==='100'?'794px':'100%';host.style.maxWidth=$('zoom').value==='100'?'none':'794px';host.parentElement.scrollLeft=0;}
function showPages(result) {
 const fragment=document.createDocumentFragment();result.previews.forEach((url,i)=>{const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=url;img.alt=`简历第 ${i+1} 页`;caption.textContent=`第 ${i+1} 页 / 共 ${result.previews.length} 页`;figure.append(img,caption);fragment.append(figure);});
 $('preview-host').replaceChildren(fragment);$('page-count').textContent=`${result.previews.length} 页`;scale();
}
async function sync() {
 clearTimeout(timer);if(!token||busy)return;
 if(editor?.editor?.view?.composing){timer=setTimeout(sync,200);return;}
 const settings={pages:Number($('pages').value),font_size:Number($('font-size').value),template_id:templateId};
 if(!validSettings(settings)){error('全文字号需为 8–18 pt，步进 0.5；预期页数需为 1–20 的整数。');return;}
 const requested=revision,snapshot=value;busy=true;rendered=-1;started=performance.now();ticker=setInterval(status,1000);$('error-box').hidden=true;status();
 try {
  const response=await fetch(snapshot.trim()?'/api/build':'/api/save',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':token},body:JSON.stringify({source:snapshot,revision:requested,...settings})});
  const result=await response.json();if(result.source_saved===true)saved=requested;
  if(!response.ok||!result.ok)throw Object.assign(new Error(result.error||'预览生成失败'),{log:result.log||''});
  if(requested!==revision)return;
  if(!snapshot.trim()){$('preview-host').replaceChildren();$('page-count').textContent='';last=null;return;}
  if(!result.previews?.length||!result.pdf_url||result.revision!==requested||result.template_id!==settings.template_id)throw new Error('当前版本尚未生成完整预览，请重试。');
  last=result;rendered=requested;showPages(result);
 }catch(e){if(requested===revision)error(e.message,e.log||'');}
 finally{busy=false;clearInterval(ticker);status();if(requested!==revision)timer=setTimeout(sync,150);}
}
function download(url,name){const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();}
$('download-source').onclick=()=>{const url=URL.createObjectURL(new Blob([value],{type:'text/markdown;charset=utf-8'}));download(url,sourceName.replace(/\.(md|markdown)$/i,'')+'.md');setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('export-pdf').onclick=()=>{if(current())download(last.pdf_url,'resume.pdf');};
$('export-png').onclick=()=>{if(current())download(last.previews.length===1?last.previews[0]+'?download=1':`/builds/${last.build_id}/previews.zip`,last.previews.length===1?'resume.png':'resume-previews.zip');};
$('build-button').onclick=sync;$('pages').oninput=changed;$('zoom').onchange=scale;
$('font-size').onchange=()=>{applyPaperStyle();changed();};
function renderTemplates(){const fragment=document.createDocumentFragment();templates.forEach(template=>{const card=document.createElement('button'),img=document.createElement('img'),name=document.createElement('strong'),description=document.createElement('span'),badge=document.createElement('span');card.className='template-card';card.type='button';card.setAttribute('aria-pressed',String(template.id===templateId));img.src='/assets/templates/thumbnails/'+encodeURIComponent(template.thumbnail);img.alt=template.name+'模板缩略图';name.textContent=template.name;description.textContent=template.description;badge.textContent=template.id===templateId?'正在使用':'使用模板';badge.className='template-badge';card.append(img,name,description,badge);card.onclick=()=>{if(template.id!==templateId){templateId=template.id;renderTemplates();applyPaperStyle();changed();}$('template-dialog').close();};fragment.append(card);});$('template-grid').replaceChildren(fragment);$('template-name').textContent=templates.find(t=>t.id===templateId)?.name||templateId;}
$('template-button').onclick=()=>$('template-dialog').showModal();$('template-close').onclick=()=>$('template-dialog').close();
$('open-button').onclick=()=>$('file-input').click();
$('file-input').onchange=async event=>{const file=event.target.files[0];if(!file||!editor)return;try{if(file.size>200000)throw new Error('文件超过 200 KB，请精简后导入。');const text=await file.text();editor.setMarkdown(text);value=text;sourceName=file.name;changed();}catch(e){error('无法导入这份文件，当前内容已保留。',e.message);}event.target.value='';};
function renderLogos(){const query=$('logo-search').value.toLowerCase(),kind=$('logo-category').value,fragment=document.createDocumentFragment();const found=logos.filter(x=>(!kind||(kind==='school')===(x.category==='school'))&&`${x.id} ${x.name} ${(x.aliases||[]).join(' ')}`.toLowerCase().includes(query));found.forEach(logo=>{const b=document.createElement('button'),img=document.createElement('img'),label=document.createElement('span');img.src='/assets/logos/'+encodeURIComponent(logo.file);img.alt='';label.textContent=logo.name;b.append(img,label);b.onclick=()=>command(()=>{editor.insertLogo(logo.id,Number($('insert-logo-size').value));$('logo-dialog').close();});fragment.append(b);});$('logo-list').replaceChildren(fragment);$('logo-empty').hidden=found.length>0;}
$('logo-search').oninput=renderLogos;$('logo-category').onchange=renderLogos;
$('logo-toggle').onclick=()=>{$('logo-dialog').showModal();$('logo-search').focus();};$('logo-close').onclick=()=>$('logo-dialog').close();
function command(action){try{action();}catch(e){error('暂时无法完成此编辑。',e.message);}}
$('bold-button').onclick=()=>command(()=>editor.toggleBold());$('undo-button').onclick=()=>editor.undo();$('redo-button').onclick=()=>editor.redo();
$('selection-size').onchange=()=>command(()=>editor.setFontSize($('selection-size').value?Number($('selection-size').value):null));
$('logo-size').onchange=()=>command(()=>editor.setLogoSize(Number($('logo-size').value)));
$('logo-size').onkeydown=e=>{if(e.key==='Enter')e.target.blur();};
$('add-block').onchange=()=>{if($('add-block').value)command(()=>editor.insertBlock($('add-block').value));$('add-block').value='';};
// Keep the editor's selection while toolbar buttons are clicked.
for(const id of ['bold-button','undo-button','redo-button','logo-toggle'])$(id).onmousedown=e=>e.preventDefault();
window.addEventListener('beforeunload',e=>{if(token&&saved!==revision){e.preventDefault();e.returnValue='';}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();sync();}});
function selection(info){$('bold-button').setAttribute('aria-pressed',String(!!info.bold));$('selection-size').value=info.fontSize?String(info.fontSize):'';$('logo-size').disabled=!info.isLogo;$('logo-size').value=String(info.logoSize||16);$('selection-hint').textContent=info.isLogo?'已选中图标，可调整大小':'选中文字可加粗、调字号；点击图标可调大小';}
(async()=>{try{const response=await fetch('/api/session');if(!response.ok)throw new Error('无法连接本机编辑服务');const session=await response.json();token=session.token;value=session.source;sourceName=session.source_name;logos=session.logos||[];templates=session.templates||[];templateId=session.template_id||'classic';saved=revision;$('download-source').disabled=false;
 if(!templates.some(t=>t.id===templateId))throw new Error('模板目录不匹配，请重启编辑服务。');
 $('pages').value=session.default_pages||1;$('font-size').value=session.font_size||10.5;
 editor=createResumeEditor({element:$('editor-host'),source:value,logos,onChange:next=>{if(next===value)return;value=next;changed();},onSelection:selection,onError:message=>error('内容暂时无法保存，请检查提示。',message)});
 for(const id of ['open-button','bold-button','undo-button','redo-button','template-button','logo-toggle','selection-size','add-block','font-size'])$(id).disabled=false;
 renderTemplates();renderLogos();applyPaperStyle();status();sync();
 }catch(e){error('编辑器暂时无法载入。可先导出原稿保留内容，再按提示处理。',e.message);$('save-state').textContent='需要处理';}})();
