'use strict';
// Map-first home and route-preview controls. Existing API/session workflows remain shared.
const sheet = $('sidebar');
const handle = el('button', undefined, 'sheet-handle');
handle.type='button';handle.setAttribute('aria-label','Expand or collapse navigation panel');handle.setAttribute('aria-expanded','false');
sheet.prepend(handle);
let sheetExpanded=false;let suppressHandleClick=false;
function setSheetHeight(height){const bounded=Math.max(160,Math.min(innerHeight*.9,height));document.documentElement.style.setProperty('--sheet-height',bounded+'px');}
function expandSheet(){sheetExpanded=true;setSheetHeight(innerHeight*.8);handle.setAttribute('aria-expanded','true');}
handle.onclick=()=>{if(suppressHandleClick){suppressHandleClick=false;return;}sheetExpanded=!sheetExpanded;setSheetHeight(innerHeight*(sheetExpanded?.8:.42));handle.setAttribute('aria-expanded',String(sheetExpanded));};
let dragStart=null;
handle.addEventListener('pointerdown',e=>{dragStart={y:e.clientY,height:sheet.getBoundingClientRect().height};handle.setPointerCapture(e.pointerId);});
handle.addEventListener('pointermove',e=>{if(!dragStart)return;setSheetHeight(dragStart.height+dragStart.y-e.clientY);});
handle.addEventListener('pointerup',e=>{if(!dragStart)return;const moved=Math.abs(dragStart.y-e.clientY)>8;dragStart=null;sheetExpanded=sheet.getBoundingClientRect().height>innerHeight*.6;handle.setAttribute('aria-expanded',String(sheetExpanded));if(moved){suppressHandleClick=true;e.preventDefault();}});
handle.addEventListener('pointercancel',()=>{dragStart=null;});
const mapMenu=el('button','☰','floating-menu');mapMenu.setAttribute('aria-label','Open navigation menu');mapMenu.onclick=()=>workflowNav.querySelector('button').click();document.body.append(mapMenu);
const heading=el('div',undefined,'route-heading');const back=btn('←',()=>{if(state.active)stopNav();state.routes=[];$('routes').replaceChildren();if(routeLayer){routeLayer.remove();routeLayer=null;}document.body.classList.remove('previewing');heading.hidden=true;avoidButton.hidden=true;setSheetHeight(innerHeight*.42);},heading);back.setAttribute('aria-label','Back to destination search');const headingLabel=el('span');heading.append(headingLabel);heading.hidden=true;document.body.append(heading);
const avoidButton=el('button','Avoid ⌄','avoid-map-button');avoidButton.onclick=avoidSettings;avoidButton.hidden=true;document.body.append(avoidButton);
const voice=el('button','🎙','voice-search');voice.type='button';voice.setAttribute('aria-label','Search by voice');$('searchForm').querySelector('.searchbox').append(voice);
let recognition=null;
voice.onclick=()=>{
 const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!Speech)return toast('Voice search is unavailable in this browser. Use the keyboard to search.');
 if(recognition){recognition.stop();return;}
 const info=modal('Voice destination search');info.append(el('p','Your browser may send audio to its speech-recognition provider. Start only when safely parked.','hint'));
 btn('Start microphone',()=>{
  $('modal').close();recognition=new Speech();recognition.lang=prefs.ui==='pcm'?'en-NG':({en:'en',fr:'fr',pt:'pt',sw:'sw',yo:'yo',ha:'ha',ar:'ar'}[prefs.ui]||'en');recognition.interimResults=false;recognition.maxAlternatives=1;
  voice.classList.add('listening');voice.setAttribute('aria-label','Stop voice search');
  recognition.onresult=e=>{const text=e.results?.[0]?.[0]?.transcript;if(text){$('search').value=text;expandSheet();$('searchForm').requestSubmit();}};
  recognition.onerror=e=>toast('Voice search: '+e.error+'. You can type your destination.');
  recognition.onend=()=>{recognition=null;voice.classList.remove('listening');voice.setAttribute('aria-label','Search by voice');};
  try{recognition.start();}catch(e){recognition=null;voice.classList.remove('listening');toast(e.message);}
 },info,'primary');
};
const addPlace=btn('＋ New',newPlace,document.querySelector('.quick'));addPlace.className='new-place';
function newPlace(label){
 const c=modal(typeof label==='string'?'Set '+label:'Add a saved place');
 if(!state.dest){c.append(el('p','Choose an address from search or tap the map first.'));btn('Search for an address',()=>{$('modal').close();expandSheet();$('search').focus();},c,'primary');return;}
 const name=field(c,'Place name','text',typeof label==='string'?label:state.dest.label);name.maxLength=100;
 c.append(el('p',state.dest.label));
 btn('Save place',guard(async()=>{if(!name.value.trim())throw Error('Enter a place name.');await api('places',{...state.dest,label:name.value.trim()});$('modal').close();await loadHome();toast('Place saved.');}),c,'primary');
}
const recentSection=el('section',undefined,'home-recents');recentSection.append(el('h2','Recent'));const recentList=el('div');recentSection.append(recentList);document.querySelector('.quick').after(recentSection);
const moreOptions=el('div',undefined,'more-options');moreOptions.append(el('p','More options'));
btn('♧ Drive to friends and family',guard(async()=>{await signedIn();const places=await api('places');const c=modal('Drive to friends and family');c.append(el('p','Choose a saved address or add one. Device contacts are not imported.','hint'));for(const place of places)btn(place.label,guard(async()=>{$('modal').close();await prepareRoute(place);}),c);btn('＋ Add an address',()=>newPlace(),c,'primary');}),moreOptions);
recentSection.after(moreOptions);
const suggestion=el('section',undefined,'destination-suggestion');suggestion.hidden=true;document.body.append(suggestion);
let dismissedSuggestion=null;
async function prepareRoute(destination){
 selectDest(destination);sheet.scrollTop=0;
 if(!state.pos){
  if(!navigator.geolocation)throw Error('GPS is unavailable. Set a starting point in Settings.');
  const position=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000}));updateLocation(position);
 }
 await loadRoutes();
}
async function loadHome(){
 const user=(await api('me')).user;recentList.replaceChildren();suggestion.replaceChildren();suggestion.hidden=true;
 if(!user){recentList.append(el('p','Sign in and enable navigation history to see recent journeys.','hint'));return;}
 const [history,places]=await Promise.all([api('history'),api('places')]);state.homePlaces=places;
 if(!history.length)recentList.append(el('p','No recent journeys. History is optional in Privacy & map.','hint'));
 for(const place of history.slice(0,5)){const row=el('div',undefined,'recent-destination');const button=btn('◷ '+place.label,guard(()=>prepareRoute(place)),row);button.title=place.label;const options=btn('⋯',()=>recentOptions(place),row);options.setAttribute('aria-label','Options for '+place.label);recentList.append(row);}
 const latest=history[0];
 if(latest&&dismissedSuggestion!==latest.id&&!state.routes.length){
  const title=el('div',undefined,'suggestion-title');title.append(el('b','Drive to '+latest.label+'?'));const info=btn('ⓘ',()=>{const c=modal('Recent destination suggestion');c.append(el('p','This address comes from your opt-in navigation history. Tap Drive there for a current route estimate, or No to dismiss it. No live traffic prediction is used.'));},title);info.setAttribute('aria-label','About this destination suggestion');suggestion.append(title,el('p','Recent destination · preview a fresh route estimate','hint'));
  const actions=el('div',undefined,'row');btn('No',()=>{dismissedSuggestion=latest.id;suggestion.hidden=true;},actions);btn('Drive there',guard(()=>prepareRoute(latest)),actions,'primary');suggestion.append(actions);suggestion.hidden=false;
 }
}
function recentOptions(place){const c=modal(place.label);btn('Drive there',guard(async()=>{$('modal').close();await prepareRoute(place);}),c,'primary');btn('Save place',()=>{selectDest(place);newPlace();},c);btn('Remove from recent',guard(async()=>{await api('history',{delete:place.id});$('modal').close();await loadHome();}),c);btn('Why is this suggested?',()=>{const c=modal('Recent destination');c.append(el('p','This destination comes from navigation history you chose to enable. No home, work schedule or travel intention is inferred. You can clear history or switch it off in Privacy & map.'));},c);}
for(const button of document.querySelectorAll('[data-quick]'))button.onclick=guard(async()=>{
 await signedIn();const places=await api('places');const place=places.find(x=>x.label.toLowerCase()===button.dataset.quick.toLowerCase());
 if(place)await prepareRoute(place);else newPlace(button.dataset.quick);
});
function avoidSettings(){
 const c=modal('Avoid roads');const supported=state.cap.routingExcludes?.[state.vehicle]||[];
 c.append(el('p','Options are enabled only for exclusion classes configured on the selected routing provider.','hint'));
 const inputs=[];
 for(const [value,label] of [['toll','Toll roads'],['motorway','Motorways'],['ferry','Ferries'],['unpaved','Unpaved roads']]){
  const row=el('label',undefined,'toggle-row');const input=el('input');input.type='checkbox';input.value=value;input.checked=state.avoid.includes(value);input.disabled=!supported.includes(value);inputs.push(input);row.append(input,document.createTextNode(label+(input.disabled?' · unavailable':'')));c.append(row);
 }
 btn('Apply and compare routes',guard(async()=>{state.avoid=inputs.filter(i=>i.checked&&!i.disabled).map(i=>i.value);$('modal').close();await loadRoutes();}),c,'primary');
}
const baseRenderRoutes=renderRoutes;
renderRoutes=function(){
 baseRenderRoutes();document.body.classList.add('previewing');heading.hidden=false;avoidButton.hidden=false;suggestion.hidden=true;headingLabel.textContent='Your location → '+state.dest.label;setSheetHeight(innerHeight*.42);sheet.scrollTop=0;
 const panel=el('div',undefined,'route-preview-tools');const vehicles=el('div',undefined,'vehicle-switch');vehicles.setAttribute('role','group');vehicles.setAttribute('aria-label','Vehicle type');
 for(const [key,label] of [['car','🚗 Car'],['motorcycle','🏍 Motorcycle']]){
  const button=btn(label,guard(async()=>{if(state.active)stopNav();state.vehicle=key;state.avoid=[];await loadRoutes();}),vehicles,key===state.vehicle?'selected':'');button.setAttribute('aria-pressed',String(state.vehicle===key));button.disabled=!state.cap.routingVehicles?.includes(key);
  if(button.disabled)button.title='Configure a '+key+' routing provider to enable this option.';
 }
 panel.append(vehicles);
 if(!state.cap.routingVehicles?.includes('motorcycle'))panel.append(el('p','Motorcycle mode needs its own routing provider.','hint'));
 $('routes').prepend(panel);
 const summaries=[...$('routes').children].filter(x=>x.classList.contains('card'));
 state.routes.forEach((route,index)=>{
  const names=[...new Set((route.legs||[]).flatMap(l=>l.steps||[]).map(s=>s.name).filter(Boolean))].slice(0,3);
  const summary=summaries[index];if(!summary)return;
  const via=el('p',names.length?'Via '+names.join(' · '):'Road names unavailable');summary.querySelector('b').after(via);
  summary.append(el('p','Estimated arrival '+new Date(Date.now()+route.duration*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})+' · no live traffic','hint'));
  btn('Leave later',()=>{state.routeIndex=index;planDrive();},summary);
 });
};
const homeApi=api;
api=async function(path,data){const result=await homeApi(path,data);if(data&&['login','register','logout','delete-account','history','places'].includes(path))queueMicrotask(()=>loadHome().catch(()=>{}));return result;};
$('search').addEventListener('focus',expandSheet);
if(prefs.dark===undefined){prefs.dark=matchMedia('(prefers-color-scheme:dark)').matches;applyMapPreferences();}
loadHome().catch(()=>{recentList.textContent='Recent destinations are unavailable. Try again from Menu → Recent journeys.';});
