const test=require('node:test');
const assert=require('node:assert/strict');
const journey=require('../web/journey.js');
const destination={lat:6.5,lon:3.3,label:'Destination'};
const source={lat:7,lon:4,label:'Source'};
test('destination and Go gets current GPS, routes, then starts navigation',async()=>{
 const calls=[];
 await journey.begin({destinationText:'Destination',resolve:async(text,kind)=>{calls.push(kind);return destination},locate:async()=>{calls.push('gps');return source},route:async value=>{assert.equal(value.manual,false);assert.deepEqual(value.source,source);calls.push('route')},start:async()=>calls.push('start')});
 assert.deepEqual(calls,['destination','gps','route','start']);
});
test('source and destination use entered source without requesting device GPS',async()=>{
 const calls=[];
 const result=await journey.begin({sourceText:'Source',destinationText:'Destination',resolve:async(text,kind)=>{calls.push(kind);return kind==='destination'?destination:source},locate:async()=>{throw Error('GPS must not be requested')},route:async value=>{assert.equal(value.manual,true);calls.push('route')},start:async()=>calls.push('start')});
 assert.deepEqual(result.source,source);assert.deepEqual(calls,['destination','starting address','route','start']);
});
test('routing failure never starts navigation',async()=>{
 let started=false;
 await assert.rejects(journey.begin({destinationText:'Destination',resolve:async()=>destination,locate:async()=>source,route:async()=>{throw Error('Routing not configured')},start:async()=>{started=true}}),/Routing not configured/);
 assert.equal(started,false);
});
test('missing destination or invalid geocoder coordinates never start routing',async()=>{
 await assert.rejects(journey.begin({destinationText:' '}),/Enter a destination/);
 await assert.rejects(journey.begin({destinationText:'Destination',resolve:async()=>({lat:Infinity,lon:3})}),/invalid coordinates/);
 assert.throws(()=>journey.place({lat:null,lon:4}),/invalid coordinates/);
});
test('location denial does not route or start',async()=>{
 let routed=false;
 await assert.rejects(journey.begin({destinationText:'Destination',resolve:async()=>destination,locate:async()=>{throw Error('Location denied')},route:async()=>{routed=true}}),/Location denied/);
 assert.equal(routed,false);
});
test('numbered street query rejects unrelated global Dublin suggestions',()=>{
 const results=['CSCC Dublin Regional Learning Center, 6190 Shamrock Court, Dublin, OH','Dublin, Ohio, 43016, United States','Green Street Court House, Dublin, Ireland','Dublin Airport, Dublin, Ireland'].map(display_name=>({display_name,lat:1,lon:2}));
 assert.deepEqual(journey.addressMatches('2105 Dublin Court',results),[]);
});
test('street abbreviation matches but wrong house numbers do not',()=>{
 const matches=journey.addressMatches('2105 Dublin Ct, McKinney TX',[{display_name:'2105 Dublin Court, McKinney, Texas',lat:1,lon:2},{display_name:'2107 Dublin Court, McKinney, Texas',lat:1,lon:2}]);
 assert.equal(matches.length,1);assert.equal(matches[0].addressAccuracy,'address');
});
test('street-only match is marked approximate rather than a verified house',()=>{
 const matches=journey.addressMatches('2105 Dublin Court',[{display_name:'Dublin Court, McKinney, Texas, 75071',lat:1,lon:2}]);
 assert.equal(matches[0].addressAccuracy,'street');
});
test('non-numbered place searches remain selectable',()=>{
 assert.equal(journey.addressMatches('Lagos',[{display_name:'Lagos, Nigeria',lat:6,lon:3}])[0].addressAccuracy,'place');
});

test('supplied city and postcode reject the same street in another location',()=>{
 const matches=journey.addressMatches('2105 Dublin Ct, McKinney TX 75071',[
 {display_name:'2105 Dublin Court, Springfield, Texas, 77001',lat:1,lon:2},
 {display_name:'2105 Dublin Court, McKinney, Texas, 75071',lat:1,lon:2}]);
 assert.equal(matches.length,1);assert.match(matches[0].display_name,/McKinney/);
});
