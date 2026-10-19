import http.client,json,os,tempfile,threading,unittest
from pathlib import Path
os.environ['ATONA_DATA']=tempfile.mkdtemp()
import server
from deploy.namecheap import merge,parse_response
class PlatformTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
 def setUp(self):server.LIMIT.clear()
 def req(self,path,body=None,cookie=None,origin=server.ORIGIN):
  c=http.client.HTTPConnection('127.0.0.1',self.http.server_port);h={}
  if cookie:h['Cookie']=cookie
  if body is not None:h.update({'Origin':origin,'Content-Type':'application/json'})
  c.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,h)
  r=c.getresponse();raw=r.read();result=(r.status,dict(r.getheaders()),json.loads(raw));c.close();return result
 def account(self,n):
  r=self.req('/api/register',{'email':n+'@example.com','password':'strong-password-123','name':n});self.assertEqual(r[0],200);self.assertIn('HttpOnly',r[1]['Set-Cookie']);return r[1]['Set-Cookie'].split(';')[0]
 def test_account_isolation_and_session_revocation(self):
  a=self.account('alice');b=self.account('bob')
  self.assertEqual(self.req('/api/places',{'label':'Home','lat':6.5,'lon':3.3},a)[0],201)
  self.assertEqual(len(self.req('/api/places',cookie=a)[2]),1)
  self.assertEqual(self.req('/api/places',cookie=b)[2],[])
  self.req('/api/logout',{},a);self.assertEqual(self.req('/api/places',cookie=a)[0],401)
 def test_origin_and_report_validation(self):
  a=self.account('charlie')
  self.assertEqual(self.req('/api/reports',{'kind':'Crash','lat':6,'lon':3},a,origin='https://evil.example')[0],403)
  self.assertEqual(self.req('/api/reports',{'kind':'Crash','lat':float('nan'),'lon':3},a)[0],400)
  self.assertEqual(self.req('/api/reports',{'kind':'Crash','lat':6,'lon':3,'note':'test'},a)[0],201)
  self.assertTrue(any(x['note']=='test' for x in self.req('/api/reports')[2]))
 def test_provider_unavailable_is_explicit(self):
  self.assertEqual(self.req('/api/search?q=Lagos')[0],503)
  self.assertEqual(self.req('/api/route?points=3,6;4,7')[0],503)
 def test_route_provider_integration_and_invalid_coordinates(self):
  os.environ['ROUTING_URL']='https://routing.example'
  original=server.upstream;urls=[]
  server.upstream=lambda url:(urls.append(url) or {'code':'Ok','routes':[{'distance':123}]})
  try:
   self.assertEqual(self.req('/api/route?points=3,6;4,7')[2]['code'],'Ok')
   self.assertIn('/route/v1/driving/3.0,6.0;4.0,7.0',urls[0])
   self.assertEqual(self.req('/api/route?points=3,999;4,7')[0],400)
  finally:server.upstream=original;os.environ.pop('ROUTING_URL')
 def test_super_admin_authorization_and_revocation(self):
  admin=self.account('operator');member=self.account('member')
  self.assertEqual(self.req('/api/admin',cookie=member)[0],403)
  with server.db() as c:
   c.execute("UPDATE users SET role='super_admin' WHERE email='operator@example.com'")
   uid=c.execute("SELECT id FROM users WHERE email='member@example.com'").fetchone()[0]
   own=c.execute("SELECT id FROM users WHERE email='operator@example.com'").fetchone()[0]
  result=self.req('/api/admin',cookie=admin);self.assertEqual(result[0],200)
  self.assertNotIn('password',result[2]['users'][0])
  self.assertEqual(self.req('/api/admin',{'id':uid,'action':'disable'},member)[0],403)
  self.assertEqual(self.req('/api/admin',{'id':own,'action':'disable'},admin)[0],400)
  self.assertEqual(self.req('/api/admin',{'id':uid,'action':'disable'},admin)[0],200)
  self.assertIsNone(self.req('/api/me',cookie=member)[2]['user'])
  self.assertEqual(self.req('/api/login',{'email':'member@example.com','password':'strong-password-123'})[0],401)
  self.assertEqual(len(self.req('/api/admin',cookie=admin)[2]['audit']),1)
 def test_account_deletion(self):
  a=self.account('delete');self.req('/api/trips',{'label':'Trip','lat':6,'lon':3,'arrival':'2026-12-01T10:00:00Z'},a)
  self.assertEqual(self.req('/api/delete-account',{},a)[0],200)
  self.assertIsNone(self.req('/api/me',cookie=a)[2]['user'])
  with server.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM users WHERE email='delete@example.com'").fetchone()[0],0)
 def test_traversal(self):self.assertEqual(self.req('/../server.py')[0],404)
class DNSTests(unittest.TestCase):
 def test_preserve_zone_and_idempotency(self):
  rows=[{'Name':'@','Type':'A','Address':'1.2.3.4','TTL':'1800'},{'Name':'mail','Type':'TXT','Address':'v=spf1 -all','TTL':'300'}]
  result=merge(rows,['africaatona'],'181.214.149.146');self.assertEqual(result[:2],rows)
  self.assertEqual(merge(result,['africaatona'],'181.214.149.146'),result);self.assertEqual(len(rows),2)
 def test_conflict_fails(self):
  with self.assertRaises(ValueError):merge([{'Name':'africaatona','Type':'CNAME','Address':'elsewhere'}],['africaatona'],'181.214.149.146')
 def test_documented_namespace(self):
  r=parse_response('<ApiResponse xmlns="http://api.namecheap.com/xml.response" Status="OK"><Host Name="x"/></ApiResponse>');self.assertEqual(r.get('Status'),'OK')
if __name__=='__main__':unittest.main()
