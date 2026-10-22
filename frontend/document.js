const punctuation = /[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/;
export function escapeText(text) { return text.replace(/[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/g, '\\$&'); }
export function validSize(value, logo = false) { const n = Number(value); return Number.isFinite(n) && n >= 8 && n <= (logo ? 48 : 32) && n * 2 === Math.floor(n * 2); }
export function parseInline(source, marks = [], depth = 0) {
 if (depth > 16) throw new Error('格式嵌套不能超过16层');
 const out = []; let buffer = '';
 const flush = () => { if(buffer) {out.push({type:'text',text:buffer,...(marks.length?{marks:[...marks]}:{})});buffer='';} };
 function closing(token,start) { for(let j=start;j<source.length;j++){if(source[j]==='\\' && punctuation.test(source[j+1]||'')){j++;continue;} if(source.startsWith(token,j))return j;} return -1; }
 for(let i=0;i<source.length;) {
  if(source[i]==='\\' && punctuation.test(source[i+1]||'')){buffer+=source[i+1];i+=2;continue;}
  if(source.startsWith('![logo:',i)){const m=source.slice(i).match(/^!\[logo:([a-z0-9][a-z0-9-]*)(?:@(\d+(?:\.\d+)?))?\]/);if(!m||!validSize(m[2]??10.5,true))throw new Error('Logo格式或尺寸无效');flush();out.push({type:'logo',attrs:{id:m[1],size:Number(m[2]??10.5)},...(marks.length?{marks:[...marks]}:{})});i+=m[0].length;continue;}
  if(source.startsWith('**',i)){const end=closing('**',i+2);if(end<0||end===i+2)throw new Error('加粗标记未闭合或为空');flush();out.push(...parseInline(source.slice(i+2,end),[...marks.filter(m=>m.type!=='bold'),{type:'bold'}],depth+1));i=end+2;continue;}
  if(source.startsWith('<size:',i)){const m=source.slice(i).match(/^<size:(\d+(?:\.\d+)?)>/);if(!m||!validSize(m[1]))throw new Error('字号需为8–32pt，步进0.5');let level=1,end=-1;for(let j=i+m[0].length;j<source.length;j++){if(source[j]==='\\'){j++;continue;}if(source.startsWith('<size:',j))level++;if(source.startsWith('</size>',j)&&!--level){end=j;break;}else if(source.startsWith('</size>',j)){} }
   if(end<0||end===i+m[0].length)throw new Error('字号标记未闭合或为空');flush();out.push(...parseInline(source.slice(i+m[0].length,end),[...marks.filter(m=>m.type!=='fontSize'),{type:'fontSize',attrs:{size:Number(m[1])}}],depth+1));i=end+7;continue;}
  if(source[i]==='['){if(marks.some(m=>m.type==='link'))throw new Error('链接不能嵌套');const end=closing('](',i+1);if(end<0)throw new Error('链接格式无效');const stop=closing(')',end+2);if(stop<0)throw new Error('链接未闭合');const href=source.slice(end+2,stop).replace(/\\([\x21-\x2f\x3a-\x40\x5b-\x60\x7b-\x7e])/g,'$1');if(!/^(https?:\/\/|mailto:)/i.test(href)||/[\s<>{}\\]/.test(href))throw new Error('仅支持http、https或mailto链接');flush();out.push(...parseInline(source.slice(i+1,end),[...marks,{type:'link',attrs:{href}}],depth+1));i=stop+1;continue;}
  if(/[<>*`]/.test(source[i])||source.startsWith('![',i))throw new Error('不支持的格式，请用反斜线转义普通标点');
  buffer+=source[i++];
 }
 flush();return out;
}
function splitEntry(text) {let parts=[''];for(let i=0;i<text.length;i++){if(text[i]==='\\'&&punctuation.test(text[i+1]||'')){parts[parts.length-1]+=text.slice(i,i+2);i++;}else if(text[i]==='|')parts.push('');else parts[parts.length-1]+=text[i];}if(parts.length!==3)throw new Error('经历标题需包含公司、职位、日期三个字段');return parts.map(x=>x.trim());}
export function markdownToDocument(source) {
 if(typeof source!=='string')throw new Error('简历必须是文本'); const content=[];
 for(const raw of source.replace(/\r\n?/g,'\n').split('\n')){if(!raw.trim())continue;let m;
  if((m=raw.match(/^!\[avatar(?::([^\]]+)\]|\]\(([^)]+)\))$/))){content.push({type:'avatar',attrs:{src:(m[1]||m[2]).trim()}});}
  else if((m=raw.match(/^### (.*)$/))){content.push({type:'entry',content:splitEntry(m[1]).map(text=>({type:'entryField',content:parseInline(text)}))});}
  else if((m=raw.match(/^(#{1,2}) (.*)$/)))content.push({type:'heading',attrs:{level:m[1].length},content:parseInline(m[2])});
  else if((m=raw.match(/^- (.*)$/))){let list=content.at(-1);if(list?.type!=='bulletList'){list={type:'bulletList',content:[]};content.push(list);}list.content.push({type:'listItem',content:[{type:'paragraph',content:parseInline(m[1])}]});}
  else {if(/^\s*(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|>|```|---|\|)/.test(raw))throw new Error('不支持的块格式或嵌套列表');content.push({type:'paragraph',content:parseInline(raw)});}
 } return {type:'doc',content:content.length?content:[{type:'paragraph'}]};
}
export function serializeInline(nodes=[]) {return nodes.map(node=>{let text;if(node.type==='text')text=escapeText(node.text);else if(node.type==='logo'){if(!validSize(node.attrs.size,true))throw new Error('Logo尺寸无效');text=`![logo:${node.attrs.id}@${node.attrs.size}]`;}else throw new Error(`不支持节点 ${node.type}`);for(const mark of [...(node.marks||[])].reverse()){if(mark.type==='bold')text=`**${text}**`;else if(mark.type==='fontSize')text=`<size:${mark.attrs.size}>${text}</size>`;else if(mark.type==='link')text=`[${text}](${mark.attrs.href.replace(/[\\()|]/g,'\\$&')})`;else throw new Error(`不支持格式 ${mark.type}`);}return text;}).join('');}
export function documentToMarkdown(doc) {return (doc.content||[]).map(node=>{if(node.type==='avatar')return `![avatar:${node.attrs.src}]`;if(node.type==='heading')return '#'.repeat(node.attrs.level)+' '+serializeInline(node.content);if(node.type==='paragraph')return serializeInline(node.content);if(node.type==='entry')return '### '+node.content.map(n=>serializeInline(n.content)).join(' | ');if(node.type==='bulletList')return node.content.map(n=>'- '+serializeInline(n.content[0].content)).join('\n');throw new Error(`不支持节点 ${node.type}`);}).join('\n')+'\n';}
