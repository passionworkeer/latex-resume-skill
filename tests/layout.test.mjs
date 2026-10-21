import test from 'node:test';
import assert from 'node:assert/strict';
import {columnSplit,logoDimensions,TEX_PT} from '../frontend/layout.js';
test('section boundary stays stable when formatting changes',()=>{
 assert.equal(columnSplit([]),null);assert.equal(columnSplit([40]),null);
 assert.equal(columnSplit([10,80,50,20]),2);assert.equal(columnSplit([10,10,10]),1);
});
test('non-square logos use the same height and width cap as includegraphics',()=>{
 assert.deepEqual(logoDimensions(24,1),{width:24*TEX_PT,height:24*TEX_PT});
 const wide=logoDimensions(24,4);assert.equal(wide.width,64*TEX_PT);assert.equal(wide.height,16*TEX_PT);
 assert.equal(logoDimensions(24,.5).width,12*TEX_PT);
});
