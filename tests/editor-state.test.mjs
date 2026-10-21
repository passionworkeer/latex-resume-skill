import test from 'node:test';
import assert from 'node:assert/strict';
import {currentArtifact,validSettings} from '../frontend/state.js';
test('export only a verified result for the current content and settings',()=>{
 assert.equal(currentArtifact({revision:4,rendered:4,busy:false,last:{ok:true}}),true);
 for(const change of [{revision:5},{rendered:3},{busy:true},{last:{ok:false}},{last:null}])assert.equal(currentArtifact({revision:4,rendered:4,busy:false,last:{ok:true},...change}),false);
});
test('switching templates invalidates an otherwise current export',()=>{
 const state={revision:4,rendered:4,busy:false,last:{ok:true,template_id:'classic'}};
 assert.equal(currentArtifact({...state,templateId:'classic'}),true);
 assert.equal(currentArtifact({...state,templateId:'minimal'}),false);
});
test('font sizes and page target match the LaTeX interface',()=>{
 for(const size of [8,9,9.5,10,10.5,11,11.5,12,16,18])assert.equal(validSettings({pages:1,font_size:size}),true);
 for(const change of [{font_size:7.5},{font_size:18.5},{font_size:10.2},{font_size:NaN},{pages:0},{pages:1.5},{pages:21}])assert.equal(validSettings({pages:1,font_size:10.5,...change}),false);
});
