'use strict';
(function(root){
  function place(value){
    const lat=Number(value?.lat),lon=Number(value?.lon);
    if(value?.lat==null||value?.lon==null||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw Error('The selected address has invalid coordinates.');
    return {lat,lon,label:String(value.label||value.display_name||'Selected location')};
  }
  function addressMatches(query,matches){
    const aliases={ct:'court',rd:'road',st:'street',ave:'avenue',ln:'lane',dr:'drive',blvd:'boulevard',cres:'crescent',ter:'terrace',pl:'place',tx:'texas',oh:'ohio',ca:'california'};
    const normalize=text=>String(text).toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim().split(/\s+/).map(token=>aliases[token]||token);
    const numbered=String(query).trim().match(/^(\d+[a-z]?(?:[-/]\d+[a-z]?)?)\s+(.+)$/i);
    if(!numbered)return matches.map(match=>({...match,addressAccuracy:'place'}));
    const house=numbered[1].toLowerCase(),rest=normalize(numbered[2]);
    const suffixes=new Set(['court','road','street','avenue','lane','drive','boulevard','way','close','crescent','terrace','place']);
    const end=rest.findIndex(token=>suffixes.has(token));
    if(end<0)return matches.map(match=>({...match,addressAccuracy:'unverified'}));
    const street=rest.slice(0,end+1),context=rest.slice(end+1);
    return matches.flatMap(match=>{
      const tokens=normalize(match.display_name||match.label||'');
      const index=tokens.findIndex((_,i)=>street.every((token,j)=>tokens[i+j]===token));
      if(index<0||context.some(token=>!tokens.includes(token)))return [];
      const before=tokens[index-1],after=tokens[index+street.length];
      const number=[before,after].find(token=>token&&/^\d+[a-z]?$/.test(token));
      if(number&&number!==house)return [];
      return [{...match,addressAccuracy:number===house?'address':'street'}];
    });
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
  const api={begin,place,addressMatches};root.AtonaJourney=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
