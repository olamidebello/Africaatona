"""Select Photon low-volume search only when no geocoder is configured.

Run as root on the hosting server; preserve other service configuration.
"""
import json, os, tempfile
from pathlib import Path

def configure(path):
    path=Path(path)
    text=path.read_text()
    values={}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '=' not in line:continue
        key,value=line.split('=',1)
        values[key.strip()]=value.strip().strip('\"\'')
    url=values.get('GEOCODER_URL','')
    updates={}
    if not url:
        updates={'GEOCODER_URL':'https://photon.komoot.io','GEOCODER_FORMAT':'photon'}
    elif url.rstrip('/')=='https://photon.komoot.io' and values.get('GEOCODER_FORMAT')!='photon':
        updates={'GEOCODER_FORMAT':'photon'}
    if updates:
        kept=[line for line in text.splitlines() if line.split('=',1)[0].strip() not in updates]
        new='\n'.join(kept+[f'{key}={value}' for key,value in updates.items()])+'\n'
        fd,name=tempfile.mkstemp(prefix='.africaatona-',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as f:f.write(new)
            os.chmod(name,0o600)
            os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)
    return {'changed':bool(updates),'provider':'photon-low-volume' if updates else 'existing-preserved'}

if __name__=='__main__':
    print(json.dumps(configure('/etc/africaatona.env')))
