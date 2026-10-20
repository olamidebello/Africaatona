'use strict';
const sourceToggle=el('button','＋ Add starting address','source-toggle');sourceToggle.type='button';sourceToggle.setAttribute('aria-expanded','false');sourceToggle.setAttribute('aria-controls','sourceFields');
const sourceFields=el('div',undefined,'source-fields');sourceFields.id='sourceFields';sourceFields.hidden=true;
const sourceLabel=el('label','Starting address');sourceLabel.htmlFor='sourceAddress';const sourceAddress=el('input');sourceAddress.id='sourceAddress';sourceAddress.type='text';sourceAddress.placeholder='House number, street, city, state / postcode';sourceAddress.autocomplete='street-address';sourceAddress.maxLength=180;
const currentLocation=el('button','Use my current location','text-button');currentLocation.type='button';sourceFields.append(sourceLabel,sourceAddress,currentLocation);
$('searchForm').prepend(sourceToggle,sourceFields);
sourceFields.append(el('p','Include the city, state or region, and postcode to avoid places with similar names.','hint'));
const destinationLabel=$('searchForm').querySelector('label[for="search"]');destinationLabel.className='destination-label';destinationLabel.textContent='Destination';
const goButton=$('searchForm').querySelector('button[type="submit"]');goButton.textContent='Go';goButton.setAttribute('aria-label','Find route and start navigation');
const goStatus=el('p','Enter your destination, then tap Go. Add a starting address if you want to begin somewhere else.','go-status');goStatus.setAttribute('role','status');goStatus.setAttribute('aria-live','polite');$('searchForm').append(goStatus);
let goBusy=false,selectedDestination=null,selectedSource=null,cancelSelection=null,inputRevision=0;
function cancelPendingSelection(){if(cancelSelection){cancelSelection();cancelSelection=null;}}
sourceToggle.onclick=()=>{inputRevision++;cancelPendingSelection();const show=sourceFields.hidden;sourceFields.hidden=!show;sourceToggle.setAttribute('aria-expanded',String(show));sourceToggle.textContent=show?'− Use current location instead':'＋ Add starting address';if(show){expandSheet();sourceAddress.focus();}else{sourceAddress.value='';selectedSource=null;state.startMode='gps';}};
currentLocation.onclick=()=>{inputRevision++;cancelPendingSelection();sourceFields.hidden=true;sourceAddress.value='';selectedSource=null;sourceToggle.textContent='＋ Add starting address';sourceToggle.setAttribute('aria-expanded','false');};
$('search').maxLength=180;$('search').addEventListener('input',()=>{inputRevision++;selectedDestination=null;cancelPendingSelection();});sourceAddress.addEventListener('input',()=>{inputRevision++;selectedSource=null;cancelPendingSelection();});
const goSelectDestination=selectDest;
selectDest=function(destination){goSelectDestination(destination);selectedDestination=AtonaJourney.place(destination);$('search').value=selectedDestination.label;};
async function chooseAddress(matches,kind){
  expandSheet();goStatus.textContent='Select the correct '+kind+' below, or edit the address.';goButton.textContent='Choose address';$('results').replaceChildren(el('p','Choose your '+kind+':','hint'));
  const edit=btn('Edit '+kind,()=>{cancelPendingSelection();(kind==='destination'?$('search'):sourceAddress).focus();},$('results'));edit.className='text-button';
  const result=await new Promise((resolve,reject)=>{
    let done=false;
    const finish=(value,error)=>{if(done)return;done=true;cancelSelection=null;if(error)reject(error);else resolve(value);};
    cancelSelection=()=>finish(null,Error('Address selection cancelled. Tap Go to try again.'));
    for(const match of matches){const label=match.display_name+(match.addressAccuracy==='street'?' — street only; house number not verified':match.addressAccuracy==='unverified'?' — address match not verified':'');btn(label,()=>{if(['street','unverified'].includes(match.addressAccuracy)&&!confirm('This is an approximate location. The house number is not verified. Use it for directions?'))return;finish(AtonaJourney.place(match));},$('results'),'result');}
    btn('Cancel',()=>cancelSelection?.(),$('results'));
  });
  $('results').replaceChildren();return result;
}
async function resolveAddress(text,kind){
  const cached=kind==='destination'?selectedDestination:selectedSource;
  if(cached&&cached.label===text)return cached;
  goStatus.textContent='Finding '+kind+'…';const lookupRevision=inputRevision;let matches;
  for(let attempt=0;attempt<2;attempt++){
    try{matches=await api('search?q='+encodeURIComponent(text));break;}
    catch(error){if(error.status!==429||attempt===1)throw error;goStatus.textContent='Waiting briefly for address search…';await new Promise(resolve=>setTimeout(resolve,Math.min(5000,Math.max(1200,(error.retryAfter||2)*1000))));}
  }
  if(lookupRevision!==inputRevision)throw Error('Address changed. Tap Go to search again.');
  matches=AtonaJourney.addressMatches(text,Array.isArray(matches)?matches:[]);
  if(!matches.length)throw Error('No matching '+kind+'. Enter the full street address with city, state and postcode, or choose a point on the map.');
  const exact=matches.length===1&&!['street','unverified'].includes(matches[0].addressAccuracy);
  const selected=exact?AtonaJourney.place(matches[0]):await chooseAddress(matches,kind);
  if(kind==='destination'){selectedDestination=selected;$('search').value=selected.label;}else{selectedSource=selected;sourceAddress.value=selected.label;}
  return selected;
}
async function getGoLocation(){
  if(!navigator.geolocation)throw Error('Location is unavailable. Add a starting address instead.');
  goStatus.textContent='Getting your current location…';
  try{const p=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000,maximumAge:0}));return {lat:p.coords.latitude,lon:p.coords.longitude,label:'Your current location'};}
  catch(error){throw Error('Could not get your location. Allow location access or add a starting address.');}
}
$('searchForm').onsubmit=async event=>{
  event.preventDefault();if(goBusy)return;goBusy=true;goButton.disabled=true;goButton.textContent='Starting…';const submittedRevision=inputRevision;$('searchForm').setAttribute('aria-busy','true');
  try{
    await AtonaJourney.begin({destinationText:$('search').value,sourceText:sourceFields.hidden?'':sourceAddress.value,resolve:resolveAddress,locate:getGoLocation,
      route:async({source,destination,manual})=>{
        if(submittedRevision!==inputRevision)throw Error('Address changed. Tap Go to start with the new addresses.');
        selectDest(destination);state.pos={lat:source.lat,lon:source.lon};state.startMode=manual?'manual':'gps';state.stop=null;
        $('gpsStatus').textContent=manual?'Entered starting point':'Current location';
        goStatus.textContent='Finding the best available road route…';await loadRoutes();
        if(!state.routes.length)throw Error('No road route is available. Check the starting and destination addresses.');
      },start:async()=>{goStatus.textContent='Starting navigation…';await start(0);}
    });
    goStatus.textContent='Navigation started.';$('results').replaceChildren();sheet.scrollTop=0;
    if(state.startMode==='manual')toast('Directions started from your entered address. Live GPS is off; use Next direction or switch to live GPS.');
  }catch(error){goStatus.textContent=error.message;toast(error.message);$('results').replaceChildren();}
  finally{goBusy=false;goButton.disabled=false;goButton.textContent=uiText('Go','Oya, go!');for(const input of [$('search'),sourceAddress,sourceToggle,currentLocation])input.disabled=false;$('searchForm').removeAttribute('aria-busy');}
};
const manualTools=el('div',undefined,'manual-navigation');manualTools.hidden=true;$('navigation').append(manualTools);
function renderManualTools(){
 manualTools.hidden=!state.active||state.startMode!=='manual';manualTools.replaceChildren();if(manualTools.hidden)return;
 manualTools.append(el('p','Directions from entered start · live GPS off','hint'));
 btn('Previous direction',()=>{state.step=Math.max(0,state.step-1);state.remaining=steps().slice(state.step).reduce((n,s)=>n+s.distance,0);showNext();},manualTools);
 btn('Next direction',()=>{const list=steps();state.step=Math.min(list.length-1,state.step+1);state.remaining=list.slice(state.step).reduce((n,s)=>n+s.distance,0);showNext();},manualTools,'primary');
 btn('Use live GPS',guard(async()=>{const source=await getGoLocation();const savedStop=state.stop;stopNav();state.stop=savedStop;state.pos=source;state.startMode='gps';await loadRoutes();await start(0);}),manualTools);
}
const goStart=start;start=async function(index){await goStart(index);document.body.classList.add('navigating');renderManualTools();sheet.scrollTop=0;};
const goStop=stopNav;stopNav=function(){goStop();document.body.classList.remove('navigating');renderManualTools();};
// Reopen the simple form without losing the current destination.
const changeJourney=btn('Change journey',()=>{stopNav();document.body.classList.remove('previewing');heading.hidden=true;avoidButton.hidden=true;expandSheet();$('search').focus();},$('navigation'));
changeJourney.className='text-button';

if(state.dest){selectedDestination=AtonaJourney.place(state.dest);$('search').value=selectedDestination.label;}

function translateGoLabels(){
 destinationLabel.textContent=uiText('Destination','Where you dey go?');
 sourceLabel.textContent=uiText('Starting address','Where you dey start from?');
 if(!goBusy)goButton.textContent=uiText('Go','Oya, go!');
 sourceToggle.textContent=sourceFields.hidden?uiText('＋ Add starting address','＋ Put where you dey start'):uiText('− Use current location instead','− Use where I dey now');
 currentLocation.textContent=uiText('Use my current location','Use where I dey now');
 if(!goBusy)goStatus.textContent=uiText('Enter your destination, then tap Go.','Put where you dey go, then press Oya, go! Make we waka.');
}
document.addEventListener('atona-language-change',translateGoLabels);translateGoLabels();
