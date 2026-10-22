import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { markdownToDocument as parse, documentToMarkdown as serialize, escapeText } from '../frontend/document.js';
for(const name of ['zh','en','logos','styles'])test(`example ${name} semantic roundtrip`,()=>{const source=readFileSync(new URL(`../skills/latex-resume/assets/templates/example-${name}.md`,import.meta.url),'utf8');const doc=parse(source);assert.deepEqual(parse(serialize(doc)),doc);});
test('nested bold size and links',()=>{for(const s of ['<size:12>中文 **粗体**</size>','**正常 <size:11.5>字号</size>**','[**作品**](https://example.com)']){const doc=parse(s);assert.deepEqual(parse(serialize(doc)),doc);}});
test('literal unicode and punctuation',()=>{const text='中文 🦀 * [] < > \\ | # _ ` !';const doc=parse(escapeText(text));assert.equal(doc.content[0].content[0].text,text);assert.deepEqual(parse(serialize(doc)),doc);});
test('logos and sizes',()=>{const doc=parse('![logo:bupt@20] ![logo:github]');assert.equal(doc.content[0].content[2].attrs.size,10.5);assert.deepEqual(parse(serialize(doc)),doc);});
test('invalid syntax never silently discarded',()=>{for(const s of ['**bad','<size:7>x</size>','<size:12>x','![logo:bupt@49]','[x](javascript:alert)','### missing | field','  - nested','`code`','<em>x</em>','<size:12></size>','[x](https://x/{})'])assert.throws(()=>parse(s),s);});
test('escaped entry separators are literal',()=>{const doc=parse('### A\\|B | C | 2026');assert.equal(doc.content[0].content[0].content[0].text,'A|B');assert.deepEqual(parse(serialize(doc)),doc);});
test('nested size selects inner size and restores outer',()=>{const doc=parse('<size:12>A<size:14>B</size>C</size>');assert.deepEqual(doc.content[0].content.map(n=>n.marks[0].attrs.size),[12,14,12]);assert.deepEqual(parse(serialize(doc)),doc);});
test('excessive nested formatting fails explicitly',()=>{assert.throws(()=>parse('<size:12>'.repeat(17)+'x'+'</size>'.repeat(17)));assert.throws(()=>parse('[a [b](https://b.com)](https://a.com)'));});

test('legacy underscore and tilde remain literal',()=>{assert.equal(parse('HOME_#&%~^').content[0].content[0].text,'HOME_#&%~^');});

test('entry links escape URL field delimiters',()=>{const doc=parse('### [A](https://example.com/a\\|b) | B | C');assert.deepEqual(parse(serialize(doc)),doc);});

test('avatar block roundtrip',()=>{for(const line of ['![avatar:photo.png]','![avatar](photo.jpg)']){const doc=parse(`# 示例\n${line}\n后端开发`);assert.equal(doc.content[1].type,'avatar');assert.equal(doc.content[1].attrs.src,line.includes('png')?'photo.png':'photo.jpg');assert.deepEqual(parse(serialize(doc)),doc);}});
