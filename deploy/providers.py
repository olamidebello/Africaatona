#!/usr/bin/env python3
"""Provision persistent regional OSRM/Nominatim providers on loopback only."""
import argparse,fcntl,json,os,secrets,shutil,subprocess,time,urllib.request
from pathlib import Path

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def output(args):return subprocess.check_output(args,text=True).strip()
def health(url,kind,timeout):
 deadline=time.time()+timeout
 while time.time()<deadline:
  try:
   with urllib.request.urlopen(url,timeout=15) as response:data=json.load(response)
   if kind=='route' and data.get('code')=='Ok' and data.get('routes'):return
   if kind=='search' and isinstance(data,list) and data:return
  except Exception:pass
  time.sleep(15)
 raise RuntimeError('Provider import/health failed; inspect docker logs africaatona-'+('routing' if kind=='route' else 'geocoder'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--pbf-url',default='https://download.geofabrik.de/africa/nigeria-latest.osm.pbf');p.add_argument('--routing-image',default='ghcr.io/project-osrm/osrm-backend:latest');p.add_argument('--geocoding-image',default='mediagis/nominatim:5.3');a=p.parse_args()
 if not a.pbf_url.startswith('https://download.geofabrik.de/') or not a.pbf_url.endswith('.osm.pbf'):raise ValueError('Use a Geofabrik HTTPS .osm.pbf extract URL')
 state=Path('/var/lib/africaatona-providers');state.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (state/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  marker=state/'dataset.json'
  if marker.exists() and json.loads(marker.read_text())['pbf_url']!=a.pbf_url:raise ValueError('Dataset change requires a separately planned reimport; existing data preserved')
  existing=[]
  for name in ['africaatona-routing','africaatona-geocoder']:
   r=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
   if r.returncode==0:
    info=json.loads(r.stdout)[0]
    if (info['Config'].get('Labels') or {}).get('managed_by')!='africaatona-providers':raise ValueError('Unmanaged container name conflict: '+name)
    existing.append(name)
  if len(existing)<2:
   mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))//1024
   if mem<16000 or shutil.disk_usage(state).free<80*1024**3:raise RuntimeError('Regional self-host import requires at least 16 GB RAM and 80 GiB free disk in this deployment profile. Use a larger provider server or authorized external endpoints.')
  # Pin resolved image digests on first use; later runs do not silently upgrade data engines.
  images={}
  for key,image in [('routing',a.routing_image),('geocoding',a.geocoding_image)]:
   file=state/(key+'-image')
   if not file.exists():
    run(['docker','pull',image]);file.write_text(output(['docker','image','inspect',image,'--format','{{index .RepoDigests 0}}']))
   images[key]=file.read_text()
  data=state/'data';data.mkdir(exist_ok=True,mode=0o755);pbf=data/'region.osm.pbf'
  if 'africaatona-routing' not in existing:
   if not pbf.exists():
    with urllib.request.urlopen(a.pbf_url,timeout=120) as src,(data/'download.partial').open('wb') as dst:shutil.copyfileobj(src,dst)
    (data/'download.partial').rename(pbf);pbf.chmod(0o644)
   if not (state/'routing-prepared').exists():
    for command in [['osrm-extract','-p','/opt/car.lua','/data/region.osm.pbf'],['osrm-partition','/data/region.osrm'],['osrm-customize','/data/region.osrm']]:
     run(['docker','run','--rm','-v',str(data)+':/data',images['routing'],*command])
    (state/'routing-prepared').touch()
   run(['docker','run','-d','--name','africaatona-routing','--label','managed_by=africaatona-providers','--restart','unless-stopped','-p','127.0.0.1:5007:5000','-v',str(data)+':/data:ro',images['routing'],'osrm-routed','--algorithm','mld','/data/region.osrm'])
  else:run(['docker','start','africaatona-routing'],stdout=subprocess.DEVNULL)
  if 'africaatona-geocoder' not in existing:
   password=state/'geocoder.env'
   if not password.exists():password.write_text('NOMINATIM_PASSWORD='+secrets.token_urlsafe(40)+'\n');password.chmod(0o600)
   run(['docker','volume','create','africaatona-geocoder-db'],stdout=subprocess.DEVNULL)
   run(['docker','run','-d','--name','africaatona-geocoder','--label','managed_by=africaatona-providers','--restart','unless-stopped','--shm-size=1g','--env-file',str(password),'-e','PBF_URL='+a.pbf_url,'-e','IMPORT_WIKIPEDIA=false','-e','THREADS=2','-v','africaatona-geocoder-db:/var/lib/postgresql/16/main','-p','127.0.0.1:8087:8080',images['geocoding']])
  else:run(['docker','start','africaatona-geocoder'],stdout=subprocess.DEVNULL)
  marker.write_text(json.dumps({'pbf_url':a.pbf_url,'routing_url':'http://127.0.0.1:5007','geocoder_url':'http://127.0.0.1:8087'}))
  # Probe locations can be customized by using external providers for other regions.
  health('http://127.0.0.1:5007/route/v1/driving/3.3792,6.5244;3.3900,6.5300?overview=false','route',600)
  health('http://127.0.0.1:8087/search?q=Lagos&format=jsonv2&limit=1','search',21600)
  print('Provider URLs populated: http://127.0.0.1:5007 and http://127.0.0.1:8087. Dataset: '+a.pbf_url)
if __name__=='__main__':main()
