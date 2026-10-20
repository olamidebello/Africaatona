const test=require('node:test'),assert=require('node:assert/strict');
const p=require('../web/pidgin.js');
test('Pidgin keeps actual turn direction and road name',()=>{const text=p.instruction({maneuver:{type:'turn',modifier:'left'},name:'Allen Avenue'});assert.match(text,/turn left/);assert.match(text,/Allen Avenue/);assert.doesNotMatch(text,/turn right/)});
test('only an actual U-turn maneuver tells driver to turn back',()=>{assert.match(p.instruction({maneuver:{type:'turn',modifier:'uturn'}}),/turn back/);assert.doesNotMatch(p.instruction({maneuver:{type:'continue',modifier:'straight'}}),/turn back/)});
test('roundabout uses returned exit number',()=>{assert.match(p.instruction({maneuver:{type:'roundabout',exit:3}}),/exit 3/)});
test('unverified community traffic does not claim heavy congestion or avoidance',()=>{assert.match(p.traffic({reported:true}),/never confirm/);assert.doesNotMatch(p.traffic({reported:true}),/no pass|no be small/);assert.equal(p.traffic({}),null);assert.match(p.traffic({verified:true,heavy:true,avoid:true}),/no be small/)});
