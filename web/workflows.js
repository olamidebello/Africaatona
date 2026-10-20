'use strict';
// Extend the navigation UI using the same authenticated, same-origin API.
const workflowNav = el('nav', undefined, 'workflow-nav');
workflowNav.setAttribute('aria-label', 'Navigation tools');
$('searchForm').before(workflowNav);
btn('☰ Menu', () => {
  const c = modal('Navigation menu');
  const grid = el('div', undefined, 'tool-grid'); c.append(grid);
  [['Saved places', saved], ['Planned drives', trips], ['Recent journeys', journeyHistory],
   ['Account & profile', profileSettings], ['Privacy & map', privacySettings],
   ['Language & sound', () => $('settings').click()], ['Support tickets', supportTickets],
   ['Route overview', () => { if(!state.routes.length)throw Error('Compare routes first.');drawRoute();$('modal').close(); }], ['Route steps', () => { if(!state.routes.length)throw Error('Compare routes first.');showSteps(state.routeIndex); }], ['Stop navigation', () => { stopNav();$('modal').close();toast('Navigation stopped.'); }], ['Features & availability', featureAvailability], ['Get Android app', () => $('download').click()]]
    .forEach(([label, action]) => btn(label, guard(action), grid));
}, workflowNav);
btn('Planned drives', guard(trips), workflowNav);
btn('Recent', guard(journeyHistory), workflowNav);
async function signedIn() {
  state.user = (await api('me')).user;
  if (!state.user) { $('account').click(); throw Error('Sign in to use this account feature.'); }
  return state.user;
}
async function journeyHistory() {
  await signedIn();
  const list = await api('history'); const c = modal('Recent journeys');
  c.append(el('p', 'History is opt-in and stores up to 100 selected navigation destinations, not a GPS trail.', 'hint'));
  if (!list.length) c.append(el('p', 'No saved history. Enable it in Privacy & map.'));
  for (const item of list) {
    const row = el('div', undefined, 'card'); row.append(el('p', new Date(item.created * 1000).toLocaleString()));
    btn(item.label, () => { selectDest(item); $('modal').close(); }, row);
    btn('Delete', guard(async () => { await api('history', {delete:item.id}); await journeyHistory(); }), row); c.append(row);
  }
  if (list.length) btn('Clear all history', guard(async () => {
    if (!confirm('Delete all navigation history?')) return;
    await api('history', {clear:true}); await journeyHistory();
  }), c, 'danger');
}
async function profileSettings() {
  const user = await signedIn(); const c = modal('Account & profile');
  c.append(el('p', user.email)); const name = field(c, 'Display name', 'text', user.name); name.maxLength=70;
  btn('Save profile', guard(async () => { await api('profile', {name:name.value}); toast('Profile updated.'); }), c, 'primary');
  c.append(el('h3', 'Change password'));
  const current = field(c, 'Current password', 'password'); current.autocomplete='current-password';
  const next = field(c, 'New password (12–128 characters)', 'password'); next.autocomplete='new-password';
  const repeat = field(c, 'Confirm new password', 'password'); repeat.autocomplete='new-password';
  btn('Change password & sign out all devices', guard(async () => {
    if (next.value !== repeat.value) throw Error('Passwords must match.');
    await api('password', {current:current.value,password:next.value});
    current.value=next.value=repeat.value=''; state.user=null; $('modal').close(); toast('Password changed. Sign in again.');
  }), c);
  btn('Sign out / delete account', () => $('account').click(), c);
}
function applyMapPreferences() {
  $('speed').hidden = prefs.showSpeed === false;
  $('speed').style.display = prefs.showSpeed === false ? 'none' : '';
  if (reportsLayer && map) {
    if (prefs.showReports === false) map.removeLayer(reportsLayer);
    else if (!map.hasLayer(reportsLayer)) reportsLayer.addTo(map);
  }
  document.body.classList.toggle('dark', !!prefs.dark); translate();
}
function privacySettings() {
  const c = modal('Privacy & map settings');
  c.append(el('p', 'History saves selected destinations to your account only when enabled. Syncing settings sends the selected preferences to this server.', 'hint'));
  for (const [key,label,fallback] of [['historyEnabled','Save navigation history',false],['showSpeed','Show GPS speed',true],['showReports','Show community report markers',true]]) {
    const row = el('label',undefined,'toggle-row'); const input=el('input');input.type='checkbox';input.checked=prefs[key]??fallback;
    input.onchange=()=>{prefs[key]=input.checked;savePrefs();applyMapPreferences();};row.append(input,document.createTextNode(label));c.append(row);
  }
  btn('Save settings to account', guard(async () => {
    await signedIn(); const data={};
    for (const key of ['units','sound','ui','dark','historyEnabled','showSpeed','showReports']) if(prefs[key]!==undefined)data[key]=prefs[key];
    await api('preferences',data);toast('Settings saved to your account.');
  }),c,'primary');
  btn('Restore account settings',guard(async()=>{await signedIn();Object.assign(prefs,await api('preferences'));savePrefs();applyMapPreferences();privacySettings();toast('Account settings restored.');}),c);
  btn('Clear server history',guard(async()=>{await signedIn();if(confirm('Delete your saved navigation history?')){await api('history',{clear:true});toast('History cleared.');}}),c,'danger');
  const a=el('a','Read privacy policy');a.href='/privacy.html';c.append(a);
}
async function supportTickets() {
  await signedIn();const list=await api('support');const c=modal('Support & map issues');
  c.append(el('p','Messages are stored for the platform administrator. For immediate help, contact dobcalldemo@gmail.com. This does not contact emergency services.','hint'));
  const subject=field(c,'Subject (3–100 characters)');subject.maxLength=100;
  c.append(el('label','Details (10–2000 characters)'));const body=el('textarea');body.rows=5;body.maxLength=2000;c.append(body);
  btn('Submit ticket',guard(async()=>{await api('support',{subject:subject.value,body:body.value});await supportTickets();toast('Support ticket submitted.');}),c,'primary');
  c.append(el('h3','Your tickets'));
  if(!list.length)c.append(el('p','No tickets yet.'));
  for(const ticket of list){const card=el('div',undefined,'card');card.append(el('b',ticket.subject),el('p',ticket.body),el('small',ticket.status+' · '+new Date(ticket.created*1000).toLocaleString()));c.append(card);}
}
async function featureAvailability() {
  const r=await fetch('/features.json');if(!r.ok)throw Error('Feature list unavailable.');const list=await r.json();const c=modal('Features & resources');
  c.append(el('p','Africa Atona implements its own community navigation. Features listed as requiring resources are not active integrations.','notice'));
  for(const feature of list){const card=el('div',undefined,'card');card.append(el('b',feature.name),el('p',feature.status),el('small',feature.resource));c.append(card);}
}
function shareDestination() {
  if(!state.dest)return toast('Choose a destination first.');
  const url=new URL('/map.html',location.origin);url.searchParams.set('lat',state.dest.lat);url.searchParams.set('lon',state.dest.lon);url.searchParams.set('label',state.dest.label);
  const c=modal('Share destination');c.append(el('p','This shares the selected destination only. It does not share your live GPS position or ETA.','hint'));
  const input=field(c,'Destination link','url',url.href);input.readOnly=true;
  btn('Copy link',guard(async()=>{await navigator.clipboard.writeText(url.href);toast('Destination link copied.');}),c);
  if(navigator.share)btn('Share…',guard(async()=>{await navigator.share({title:'Africa Atona destination',url:url.href});}),c,'primary');
}
// Keep destination actions together as the selected destination changes.
const destinationActions=new MutationObserver(()=>{
  if(!state.dest||$('destination').querySelector('[data-destination-tools]'))return;
  const row=el('div',undefined,'row');row.dataset.destinationTools='true';
  btn('Share destination',shareDestination,row);
  btn('Clear stop',()=>{if(state.active)stopNav();state.stop=null;state.routes=[];$('routes').replaceChildren();if(routeLayer){routeLayer.remove();routeLayer=null;}toast('Stop removed. Compare routes to refresh.');},row);
  $('destination').append(row);
});destinationActions.observe($('destination'),{childList:true});
// Record a destination only after navigation is explicitly started and history is enabled.
const originalStart=start;
start=async function(index){
  if(!navigator.geolocation&&state.startMode!=='manual')throw Error('GPS navigation is unavailable on this device.');
  await originalStart(index);
  if(prefs.historyEnabled)try{if((await api('me')).user)await api('history',{...state.dest});}catch(e){toast('Navigation started; history not saved: '+e.message);}
};
const originalSaved=saved;
saved=async function(){
  await originalSaved();
  const list=state.savedPlaces||[];const rows=$('modalContent').querySelectorAll('.row');
  rows.forEach((row,index)=>{const place=list[index];if(!place)return;btn('Rename',guard(async()=>{const label=prompt('New place name',place.label);if(!label?.trim())return;await api('places',{...place,label:label.trim()});await saved();}),row);});
};
$('saved').onclick=guard(saved);
const originalRefresh=refreshReports;
refreshReports=async function(){
  await originalRefresh();applyMapPreferences();
  const list=state.latestReports||[];const cards=$('reports').querySelectorAll('.card');
  cards.forEach((card,index)=>{const report=list[index];if(!report)return;
    card.append(el('p',`${report.confirmations} confirmations · ${report.cleared} no longer there`,'hint'));
    for(const [label,value] of [['Still there',1],['Not there',-1]])btn(label,guard(async()=>{await api('report-vote',{id:report.id,value});await refreshReports();}),card);
  });
};
const destinationParams=new URLSearchParams(location.search);
if(destinationParams.has('lat')&&destinationParams.has('lon')){
  const lat=Number(destinationParams.get('lat')),lon=Number(destinationParams.get('lon'));
  if(Number.isFinite(lat)&&Number.isFinite(lon)&&Math.abs(lat)<=90&&Math.abs(lon)<=180){selectDest({lat,lon,label:(destinationParams.get('label')||'Shared destination').slice(0,180)});map?.setView([lat,lon],14);}
}
applyMapPreferences();

const categoryTools=el('div',undefined,'workflow-nav');
categoryTools.setAttribute('aria-label','Find places');
for(const [label,term] of [['Fuel','fuel station'],['Parking','parking'],['Charging','EV charging station'],['Food','restaurant']])btn(label,()=>{
  $('search').value=state.pos?`${term} near ${state.pos.lat.toFixed(3)}, ${state.pos.lon.toFixed(3)}`:term;
  $('search').dispatchEvent(new Event('input'));$('search').focus();
  toast('Place search only; live prices, availability and booking are not connected.');
},categoryTools);
$('results').after(categoryTools);
