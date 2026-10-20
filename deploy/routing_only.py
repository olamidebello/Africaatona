#!/usr/bin/env python3
"""Install an isolated Texas OSRM engine; preserve configured providers and data."""
import argparse, fcntl, json, os, shutil, subprocess, tempfile, time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
STATE=Path('/var/lib/africaatona-texas-routing')
ENV=Path('/etc/africaatona.env')
NAME='africaatona-texas-routing'
PBF='https://download.geofabrik.de/north-america/us/texas-latest.osm.pbf'
LOCAL='http://127.0.0.1:5008'
PROBE='/route/v1/driving/-96.6398,33.1972;-95.3698,29.7604?overview=false&steps=true&radiuses=1000;1000'
def values(path=ENV):
 result={}
 for line in Path(path).read_text().splitlines():
  if line.strip() and not line.lstrip().startswith('#') and '=' in line:
   key,value=line.split('=',1);result[key.strip()]=value.strip().strip('\"\'')
 return result
def capacity():
 mem={line.split(':',1)[0]:int(line.split()[1])//1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
 free=shutil.disk_usage('/var/lib').free//(1024**3)
 return dict(ram_mb=mem['MemTotal'],available_mb=mem['MemAvailable'],free_gib=free,ready=mem['MemTotal']>=8000 and mem['MemAvailable']>=6000 and free>=32)
def configured(url):
 if any(char.isspace() for char in url):raise ValueError('Provider URL must not contain whitespace')
 p=urlparse(url)
 if not (p.scheme=='https' and p.hostname) and url!=LOCAL:raise ValueError('Use an HTTPS OSRM-compatible provider or the managed local endpoint')
 return url.rstrip('/')
def write_config(url,region,path=ENV):
 path=Path(path);text=path.read_text();updates={'ROUTING_URL':url,'ROUTING_REGION':region}
 lines=[line for line in text.splitlines() if line.split('=',1)[0].strip() not in updates]
 content='\n'.join(lines+[f'{key}={value}' for key,value in updates.items()])+'\n'
 if text==content:return False
 fd,name=tempfile.mkstemp(prefix='.atona-routing-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:f.write(content)
  os.chmod(name,0o600);os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)
 return True
def run(args):subprocess.run(args,check=True)
def output(args):return subprocess.check_output(args,text=True).strip()
def verify(base):
 with urlopen(base+PROBE,timeout=30) as r:data=json.load(r)
 if data.get('code')!='Ok' or not data.get('routes') or not data['routes'][0].get('legs'):raise RuntimeError('Provider did not return a Texas road route with instructions')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--inspect',action='store_true');args=parser.parse_args()
 existing=values().get('ROUTING_URL','');supplied=os.getenv('ATONA_ROUTING_URL','').strip()
 if args.inspect:
  print(json.dumps(dict(configured=bool(existing),external=bool(supplied),capacity=capacity())));return
 if existing:
  print(json.dumps({'changed':False,'provider':'existing-preserved'}));return
 if supplied:
  base=configured(supplied);verify(base);changed=write_config(base,'Configured provider');print(json.dumps({'changed':changed,'provider':'external-verified'}));return
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (STATE/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  inspect=subprocess.run(['docker','inspect',NAME],capture_output=True,text=True)
  if inspect.returncode==0:
   info=json.loads(inspect.stdout)[0]
   if (info['Config'].get('Labels') or {}).get('managed_by')!='africaatona-texas-routing':raise RuntimeError('Unmanaged routing container name conflict')
   run(['docker','start',NAME])
  else:
   cap=capacity()
   if not cap['ready']:raise RuntimeError('Texas routing import needs at least 8 GB total RAM, 6 GB currently available RAM and 32 GiB free disk. Existing application is preserved. Configure ATONA_ROUTING_URL for a separately hosted compatible provider instead.')
   imagefile=STATE/'image-digest'
   if not imagefile.exists():
    image='ghcr.io/project-osrm/osrm-backend:latest';run(['docker','pull',image]);imagefile.write_text(output(['docker','image','inspect',image,'--format','{{index .RepoDigests 0}}']))
   image=imagefile.read_text().strip();data=STATE/'data';data.mkdir(exist_ok=True,mode=0o755)
   metadata=STATE/'dataset.json'
   if metadata.exists() and json.loads(metadata.read_text()).get('url')!=PBF:raise RuntimeError('Dataset changed; separate reimport required')
   metadata.write_text(json.dumps({'url':PBF,'region':'Texas, United States'}))
   pbf=data/'region.osm.pbf'
   if not pbf.exists():
    with urlopen(PBF,timeout=120) as src,(data/'download.partial').open('wb') as dst:shutil.copyfileobj(src,dst)
    if (data/'download.partial').stat().st_size<1000000:raise RuntimeError('Map download is incomplete')
    (data/'download.partial').replace(pbf);pbf.chmod(0o644)
   memory=str(max(4,min(12,cap['available_mb']//1024-2)))+'g'
   for step,command in [('extract',['osrm-extract','--threads','2','-p','/opt/car.lua','/data/region.osm.pbf']),('partition',['osrm-partition','--threads','2','/data/region.osrm']),('customize',['osrm-customize','--threads','2','/data/region.osrm'])]:
    marker=STATE/(step+'-complete')
    if not marker.exists():run(['docker','run','--rm','--cpus','2','--memory',memory,'-v',str(data)+':/data',image,*command]);marker.touch()
   run(['docker','run','-d','--name',NAME,'--label','managed_by=africaatona-texas-routing','--restart','unless-stopped','--cpus','2','--memory',memory,'-p','127.0.0.1:5008:5000','-v',str(data)+':/data:ro',image,'osrm-routed','--algorithm','mld','--threads','2','/data/region.osrm'])
  for attempt in range(30):
   try:verify(LOCAL);break
   except Exception:
    if attempt==29:raise RuntimeError('Texas routing health check failed; inspect docker logs '+NAME)
    time.sleep(5)
  changed=write_config(LOCAL,'Texas, United States')
  print(json.dumps({'changed':changed,'provider':'local-texas-verified'}))
if __name__=='__main__':main()
