"""Install an APK from a specific versioned GitHub release, verifying its checksum."""
import hashlib,json,os,re,sys,tempfile,urllib.request
from pathlib import Path

def download(url,limit):
 if not url.startswith('https://github.com/olamidebello/') and not url.startswith('https://api.github.com/repos/olamidebello/'):raise ValueError('Untrusted download URL')
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AFRICA-ATONA-deployer'}),timeout=60) as r:
  body=r.read(limit+1)
  if len(body)>limit:raise ValueError('Asset too large')
  return body

def main():
 repo=sys.argv[1]; tag=sys.argv[2]; dest=Path(sys.argv[3])
 if repo not in ['Africaatona','africanappsstore'] or not re.fullmatch(r'atona-beta-[0-9]+',tag):raise ValueError('Select an AFRICA ATONA versioned beta release')
 release=json.loads(download(f'https://api.github.com/repos/olamidebello/{repo}/releases/tags/{tag}',1000000))
 assets={a['name']:a['browser_download_url'] for a in release['assets']}
 expected=download(assets['africa-atona.apk.sha256'],1000).decode().split()[0]
 raw=download(assets['africa-atona.apk'],100000000)
 if not re.fullmatch('[0-9a-f]{64}',expected) or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('APK checksum mismatch')
 if not raw.startswith(b'PK'):raise ValueError('Not an Android archive')
 dest.mkdir(exist_ok=True,parents=True)
 for name,data in [('africa-atona.apk',raw),('africa-atona.apk.sha256',(expected+'  africa-atona.apk\n').encode())]:
  with tempfile.NamedTemporaryFile(dir=dest,delete=False) as f:f.write(data);temp=f.name
  os.chmod(temp,0o644);os.replace(temp,dest/name)
 print('Verified APK installed')
if __name__=='__main__':main()
