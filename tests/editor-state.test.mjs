import test from 'node:test';
import assert from 'node:assert/strict';
import {currentArtifact,validSettings} from '../frontend/state.js';
test('export only a verified result for the current content and settings',()=>{
 assert.equal(currentArtifact({revision:4,rendered:4,busy:false,last:{ok:true}}),true);
 for(const change of [{revision:5},{rendered:3},{busy:true},{last:{ok:false}},{last:null}])assert.equal(currentArtifact({revision:4,rendered:4,busy:false,last:{ok:true},...change}),false);
});
test('font sizes and page target match the LaTeX interface',()=>{
 for(const size of [9,9.5,10,10.5,11,11.5,12])assert.equal(validSettings({pages:1,font_size:size}),true);
 for(const change of [{font_size:8},{font_size:12.5},{font_size:10.2},{font_size:NaN},{pages:0},{pages:1.5},{pages:21}])assert.equal(validSettings({pages:1,font_size:10.5,...change}),false);
});
