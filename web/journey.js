'use strict';
(function(root){
  function place(value){
    const lat=Number(value?.lat),lon=Number(value?.lon);
    if(value?.lat==null||value?.lon==null||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw Error('The selected address has invalid coordinates.');
    return {lat,lon,label:String(value.label||value.display_name||'Selected location')};
  }
  async function begin(options){
    const destinationText=String(options.destinationText||'').trim();
    const sourceText=String(options.sourceText||'').trim();
    if(destinationText.length<3)throw Error('Enter a destination address.');
    const destination=place(await options.resolve(destinationText,'destination'));
    const manual=sourceText.length>0;
    const source=place(manual?await options.resolve(sourceText,'starting address'):await options.locate());
    await options.route({source,destination,manual});
    await options.start();
    return {source,destination,manual};
  }
  const api={begin,place};root.AtonaJourney=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
