// The split uses visible Unicode characters, shared with templates.column_split.
export const TEX_PT = 96 / 72.27;
export const A4_WIDTH = 210 * 96 / 25.4;
export function columnSplit(weights) {
 if(weights.length<2)return null;
 const half=weights.reduce((a,b)=>a+b,0)/2;let prefix=0,best=Infinity,split=1;
 for(let i=0;i<weights.length-1;i++){prefix+=weights[i];const distance=Math.abs(prefix-half);if(distance<best){best=distance;split=i+1;}}
 return split;
}
export function documentSections(doc) {
 const sections=[];const headers=[];
 doc.forEach((node,pos)=>{
  if(node.type.name==='heading'&&node.attrs.level===2)sections.push({pos,weight:0});
  if(!sections.length)headers.push({pos,size:node.nodeSize,name:node.type.name==='heading'});
  else sections.at(-1).weight+=[...node.textContent.replace(/\s/gu,'')].length;
 });
 return {sections,headers,split:columnSplit(sections.map(s=>s.weight))};
}
export function logoDimensions(size,ratio=1){const r=Number.isFinite(ratio)&&ratio>0?ratio:1;const height=Math.min(size,size*8/3/r);return {width:height*r*TEX_PT,height:height*TEX_PT};}
export function applyTemplate(host,layout,fontSize){
 if(!layout)throw new Error('模板排版参数缺失，请重启编辑服务后刷新。');
 const variables={
  'tex-pt':`${TEX_PT}px`,'body-size':`${fontSize*TEX_PT}px`,'body-line':`${fontSize*layout.line_ratio*TEX_PT}px`,
  'name-size':`${layout.name_size*TEX_PT}px`,'name-line':`${layout.name_line*TEX_PT}px`,
  'section-before':`${layout.section_before*TEX_PT}px`,'section-after':`${layout.section_after*TEX_PT}px`,
  'entry-before':`${layout.entry_before*TEX_PT}px`,'body-color':layout.colors.bodygray,'strong-color':layout.colors.stronggray,'link-color':layout.colors.linkblue,
 };
 for(const side of ['top','bottom','left','right'])variables[`page-${side}`]=`${layout.margins[side]}mm`;
 for(const [key,value] of Object.entries(variables))host.style.setProperty(`--${key}`,value);
}
export function fitPapers(editorHost,previewHost,mode='fit'){
 const available=el=>el.clientWidth-parseFloat(getComputedStyle(el).paddingLeft)-parseFloat(getComputedStyle(el).paddingRight);
 const zoom=mode==='100'?1:Math.min(1,Math.max(0.1,Math.min(available(editorHost),available(previewHost.parentElement))/A4_WIDTH));
 const paper=editorHost.querySelector('.paper-sheet');if(paper)paper.style.zoom=String(zoom);
 previewHost.style.width=`${A4_WIDTH*zoom}px`;previewHost.style.maxWidth='none';
}
