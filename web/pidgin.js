'use strict';
(function(root){
 function instruction(step){
  const m=step.maneuver||{};
  const direction={'left':'left','right':'right','slight left':'small left','slight right':'small right','sharp left':'sharp left','sharp right':'sharp right','straight':'straight'}[m.modifier];
  let text;
  if(m.type==='arrive')text='You don reach! Na here your waka end. Welcome o!';
  else if(m.type==='depart')text='Oya, make we move. Follow this road.';
  else if(m.modifier==='uturn')text='Oya, turn back where road allow am.';
  else if(['roundabout','rotary','roundabout turn'].includes(m.type))text=m.exit?'For roundabout, take exit '+m.exit+'. No rush o!':'Enter roundabout; follow the road direction.';
  else if(['exit roundabout','exit rotary'].includes(m.type))text='Comot for roundabout here.';
  else if(m.type==='merge')text='Join the road'+(direction?' for '+direction:'')+'. Check well before you enter.';
  else if(['on ramp','off ramp'].includes(m.type))text=(m.type==='on ramp'?'Enter the ramp':'Comot through the ramp')+(direction?' for '+direction:'')+'.';
  else if(m.type==='fork')text='For where road divide, follow '+(direction||'the route we show you')+'.';
  else if(m.type==='turn'&&direction)text='Oya, turn '+direction+' for the next junction.';
  else if(['continue','new name','notification'].includes(m.type))text='Dey go '+(direction||'straight')+'. You dey on your way.';
  else if(m.type==='end of road')text='For where this road end, follow '+(direction||'the route we show you')+'.';
  else text='Follow the route we show you'+(direction?' for '+direction:'')+'.';
  return text+(step.name?' · '+step.name:'');
 }
 function traffic(info){
  if(info?.verified&&info?.heavy&&info?.avoid)return 'Abeg no pass that road; the traffic wey go hold you no be small. Follow the other route.';
  if(info?.reported)return 'Dem report traffic for here o. E never confirm; check road well.';
  return null;
 }
 const api={instruction,traffic,reroute:'You don miss road o. No wahala, make I find another way.',arrive:'You don reach! Na here your waka end. Welcome o!',welcome:'Welcome to Africa Atona. Where you dey go? Oya, make we waka together.'};
 root.AtonaPidgin=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
