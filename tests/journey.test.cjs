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
