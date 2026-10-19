#!/usr/bin/env python3
"""AFRICA ATONA: same-origin API and static hosting; Python standard library."""
import hashlib, hmac, json, math, os, secrets, sqlite3, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen
ROOT=Path(__file__).parent
DATA=Path(os.getenv('ATONA_DATA','./data')); DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'atona.db'
ORIGIN=os.getenv('PUBLIC_URL','https://africaatona.africandroid.world').rstrip('/')
KINDS=['Traffic','Police','Crash','Road hazard','Bad weather','Blocked lane','Road closure','Animals','Map issue','Add a place','Gas prices']
LOCK=threading.Lock(); LIMIT={}; CACHE={}
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE,name TEXT,salt TEXT,password TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires REAL); CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,user_id INTEGER,kind TEXT,lat REAL,lon REAL,note TEXT,created REAL); CREATE TABLE IF NOT EXISTS places(id INTEGER PRIMARY KEY,user_id INTEGER,label TEXT,lat REAL,lon REAL); CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY,user_id INTEGER,label TEXT,lat REAL,lon REAL,arrival TEXT);''')
  columns={r[1] for r in c.execute('PRAGMA table_info(users)')}
  if 'role' not in columns:c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
  if 'disabled' not in columns:c.execute('ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0')
  c.execute('CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,target INTEGER,created REAL)')
def password(p,s): return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def coord(lat,lon):
 lat,lon=float(lat),float(lon)
 if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Invalid coordinates')
 return lat,lon
def upstream(url):
 with urlopen(Request(url,headers={'User-Agent':'AFRICA-ATONA/1.0 ('+ORIGIN+')'}),timeout=15) as r:
  raw=r.read(6000001)
  if len(raw)>6000000: raise ValueError('Provider response too large')
  return json.loads(raw)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def send(self,status,obj,headers=None):
  body=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
  self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store')
  self.security()
  for k,v in (headers or {}).items(): self.send_header(k,v)
  self.end_headers(); self.wfile.write(body)
 def security(self):
  self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','strict-origin-when-cross-origin'); self.send_header('X-Frame-Options','DENY')
 def user(self):
  from http.cookies import SimpleCookie
  cookie=SimpleCookie(); cookie.load(self.headers.get('Cookie','')); token=cookie.get('atona')
  if token:
   with db() as c:
    row=c.execute('SELECT users.id,email,name,role FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>? AND disabled=0',(hashlib.sha256(token.value.encode()).hexdigest(),time.time())).fetchone()
    if row: return dict(row)
  return None
 def do_GET(self):
  try: self.get()
  except (ValueError,KeyError,TypeError): self.send(400,{'error':'Invalid request'})
  except Exception: self.send(502,{'error':'Service unavailable. Please try again.'})
 def get(self):
  p=urlparse(self.path); q=parse_qs(p.query)
  if p.path=='/api/admin':
   user=self.user()
   if not user or user['role']!='super_admin':return self.send(403,{'error':'Super administrator access required'})
   with db() as c:
    users=[dict(r) for r in c.execute('SELECT id,email,name,role,disabled FROM users ORDER BY id DESC LIMIT 500')]
    reports=[dict(r) for r in c.execute('SELECT id,user_id,kind,note,created FROM reports ORDER BY id DESC LIMIT 200')]
    audit=[dict(r) for r in c.execute('SELECT * FROM admin_audit ORDER BY id DESC LIMIT 200')]
    counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('users','sessions','reports','places','trips')}
   return self.send(200,dict(users=users,reports=reports,audit=audit,counts=counts,providers={'routing':bool(os.getenv('ROUTING_URL')),'geocoding':bool(os.getenv('GEOCODER_URL'))}))
  if p.path=='/api/health': return self.send(200,{'ok':True,'application':'AFRICA ATONA'})
  if p.path=='/api/me': return self.send(200,{'user':self.user()})
  if p.path=='/api/capabilities': return self.send(200,{'routing':bool(os.getenv('ROUTING_URL')),'search':bool(os.getenv('GEOCODER_URL')),'liveTraffic':False,'speedLimits':False,'reportKinds':KINDS,'apk':(ROOT/'web/downloads/africa-atona.apk').is_file()})
  if p.path=='/api/reports':
   with db() as c: rows=c.execute('SELECT id,kind,lat,lon,note,created FROM reports WHERE created>? ORDER BY created DESC LIMIT 250',(time.time()-7200,)).fetchall()
   return self.send(200,[dict(x) for x in rows])
  if p.path in ['/api/places','/api/trips']:
   user=self.user()
   if not user:return self.send(401,{'error':'Sign in first'})
   table=p.path.split('/')[-1]
   with db() as c: rows=c.execute('SELECT * FROM '+table+' WHERE user_id=? ORDER BY id DESC',(user['id'],)).fetchall()
   return self.send(200,[dict(x) for x in rows])
  if p.path in ['/api/search','/api/route']:
   ip=self.headers.get('X-Real-IP',self.client_address[0]); now=time.time()
   with LOCK:
    bucket=LIMIT.setdefault(ip,[]); bucket[:]=[t for t in bucket if t>now-60]
    if len(bucket)>=30:return self.send(429,{'error':'Please wait before another search'})
    bucket.append(now)
    if len(LIMIT)>10000: LIMIT.clear()
   if p.path=='/api/search':
    base=os.getenv('GEOCODER_URL','')
    if not base:return self.send(503,{'error':'Destination search is awaiting a geocoding provider. Tap the map to select a destination.'})
    term=q.get('q',[''])[0].strip()[:180]
    if len(term)<3:raise ValueError()
    url=base.rstrip('/')+'/search?'+urlencode({'q':term,'format':'jsonv2','limit':8})
   else:
    base=os.getenv('ROUTING_URL','')
    if not base:return self.send(503,{'error':'Road routing is awaiting a routing provider.'})
    points=q.get('points',[''])[0].split(';')
    if not 2<=len(points)<=4:raise ValueError()
    normalized=[]
    for point in points:
     lon,lat=point.split(','); lat,lon=coord(lat,lon); normalized.append(f'{lon},{lat}')
    url=base.rstrip('/')+'/route/v1/driving/'+';'.join(normalized)+'?overview=full&geometries=geojson&steps=true&alternatives=true'
   with LOCK: hit=CACHE.get(url)
   if hit and hit[0]>now:return self.send(200,hit[1])
   result=upstream(url)
   with LOCK:
    if len(CACHE)>500:CACHE.clear()
    CACHE[url]=(now+60,result)
   return self.send(200,result)
  target=(ROOT/'web'/p.path.lstrip('/')).resolve()
  if p.path=='/':target=ROOT/'web/index.html'
  if not target.is_relative_to((ROOT/'web').resolve()) or not target.is_file():return self.send(404,{'error':'Not found'})
  import mimetypes
  body=target.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(target))[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(body))); self.security(); self.end_headers(); self.wfile.write(body)
 def do_POST(self):
  try:
   if self.headers.get('Origin')!=ORIGIN:return self.send(403,{'error':'Origin rejected'})
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=12000:return self.send(413,{'error':'Request size rejected'})
   b=json.loads(self.rfile.read(size)); path=urlparse(self.path).path
   if not isinstance(b,dict):raise ValueError()
   ip=self.headers.get('X-Real-IP',self.client_address[0]); now=time.time()
   with LOCK:
    key='post:'+ip; bucket=LIMIT.setdefault(key,[]); bucket[:]=[t for t in bucket if t>now-60]
    if len(bucket)>=20:return self.send(429,{'error':'Too many requests; wait one minute'})
    bucket.append(now)
   if path in ['/api/register','/api/login']:
    email=str(b.get('email','')).lower().strip()[:254]; pw=str(b.get('password',''))
    if '@' not in email or not 12<=len(pw)<=128: return self.send(400,{'error':'Use an email and a password of 12–128 characters'})
    with db() as c:
     if path.endswith('register'):
      salt=secrets.token_hex(16)
      try:c.execute('INSERT INTO users(email,name,salt,password) VALUES(?,?,?,?)',(email,str(b.get('name','Driver'))[:70],salt,password(pw,salt)))
      except sqlite3.IntegrityError:return self.send(409,{'error':'Account already exists'})
     row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
     if not row or row['disabled'] or not hmac.compare_digest(row['password'],password(pw,row['salt'])):return self.send(401,{'error':'Email or password incorrect'})
     token=secrets.token_urlsafe(32); c.execute('DELETE FROM sessions WHERE expires<?',(now,)); c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],now+86400*7))
    return self.send(200,{'ok':True},{'Set-Cookie':f'atona={token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=604800'})
   user=self.user()
   if not user:return self.send(401,{'error':'Sign in first'})
   if path=='/api/admin':
    if user['role']!='super_admin':return self.send(403,{'error':'Super administrator access required'})
    target=int(b['id']);action=b['action']
    with db() as c:
     if action=='delete_report':
      if not c.execute('SELECT 1 FROM reports WHERE id=?',(target,)).fetchone():raise ValueError()
      c.execute('DELETE FROM reports WHERE id=?',(target,))
     elif action in ('disable','enable','grant_admin','remove_admin','revoke_sessions'):
      if not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():raise ValueError()
      if target==user['id'] and action in ('disable','remove_admin'):return self.send(400,{'error':'Cannot remove your own access'})
      if action in ('disable','enable'):c.execute('UPDATE users SET disabled=? WHERE id=?',(int(action=='disable'),target))
      if action in ('grant_admin','remove_admin'):c.execute('UPDATE users SET role=? WHERE id=?',('super_admin' if action=='grant_admin' else 'user',target))
      c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
     else:raise ValueError()
     c.execute('INSERT INTO admin_audit(actor,action,target,created) VALUES(?,?,?,?)',(user['id'],action,target,time.time()))
    return self.send(200,{'ok':True})
   if path=='/api/logout':
    from http.cookies import SimpleCookie
    cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''))
    if cookies.get('atona'):
     with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(cookies['atona'].value.encode()).hexdigest(),))
    return self.send(200,{'ok':True},{'Set-Cookie':'atona=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0'})
   if path=='/api/delete-account':
    with db() as c:
     for table in ['sessions','reports','places','trips']:c.execute('DELETE FROM '+table+' WHERE user_id=?',(user['id'],))
     c.execute('DELETE FROM users WHERE id=?',(user['id'],))
    return self.send(200,{'ok':True},{'Set-Cookie':'atona=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0'})
   if path in ['/api/reports','/api/places','/api/trips']:
    table=path.split('/')[-1]
    if b.get('delete'):
     with db() as c:c.execute('DELETE FROM '+table+' WHERE id=? AND user_id=?',(int(b['delete']),user['id']))
     return self.send(200,{'ok':True})
    lat,lon=coord(b['lat'],b['lon'])
    with db() as c:
     if table=='reports':
      if b['kind'] not in KINDS:raise ValueError()
      c.execute('INSERT INTO reports(user_id,kind,lat,lon,note,created) VALUES(?,?,?,?,?,?)',(user['id'],b['kind'],lat,lon,str(b.get('note',''))[:300],now))
     elif table=='places':c.execute('INSERT INTO places(user_id,label,lat,lon) VALUES(?,?,?,?)',(user['id'],str(b['label'])[:100],lat,lon))
     else:c.execute('INSERT INTO trips(user_id,label,lat,lon,arrival) VALUES(?,?,?,?,?)',(user['id'],str(b['label'])[:100],lat,lon,str(b['arrival'])[:40]))
    return self.send(201,{'ok':True})
   self.send(404,{'error':'Not found'})
  except (ValueError,KeyError,TypeError,json.JSONDecodeError): self.send(400,{'error':'Invalid request'})
  except Exception: self.send(500,{'error':'Unable to save. Please try again.'})
if __name__=='__main__':
 init(); ThreadingHTTPServer(('127.0.0.1',int(os.getenv('PORT','8097'))),Handler).serve_forever()
