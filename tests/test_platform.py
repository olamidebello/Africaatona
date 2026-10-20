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
 def test_preferences_history_isolation_and_opt_out(self):
  a=self.account('history-a');b=self.account('history-b')
  place={'label':'Destination','lat':6.5,'lon':3.3}
  self.assertEqual(self.req('/api/history',place,a)[0],409)
  self.assertEqual(self.req('/api/preferences',{'historyEnabled':True,'units':'mi','ui':'pcm'},a)[0],200)
  self.assertEqual(self.req('/api/history',place,a)[0],200)
  self.assertEqual(len(self.req('/api/history',cookie=a)[2]),1)
  self.assertEqual(self.req('/api/history',cookie=b)[2],[])
  self.assertEqual(self.req('/api/preferences',{'units':'invalid'},a)[0],400)
  self.assertEqual(self.req('/api/preferences',{'historyEnabled':False},a)[0],200)
  self.assertEqual(self.req('/api/history',cookie=a)[2],[])
 def test_profile_password_revokes_sessions(self):
  a=self.account('profile')
  self.assertEqual(self.req('/api/profile',{'name':'Updated Driver'},a)[0],200)
  self.assertEqual(self.req('/api/me',cookie=a)[2]['user']['name'],'Updated Driver')
  self.assertEqual(self.req('/api/password',{'current':'wrong','password':'replacement-password-123'},a)[0],403)
  self.assertEqual(self.req('/api/password',{'current':'strong-password-123','password':'replacement-password-123'},a)[0],200)
  self.assertIsNone(self.req('/api/me',cookie=a)[2]['user'])
  self.assertEqual(self.req('/api/login',{'email':'profile@example.com','password':'replacement-password-123'})[0],200)
 def test_report_vote_replacement_and_ownership(self):
  a=self.account('reporter');b=self.account('voter')
  self.req('/api/reports',{'kind':'Traffic','lat':6,'lon':3,'note':'vote target'},a)
  report=next(r for r in self.req('/api/reports')[2] if r['note']=='vote target')
  self.assertEqual(self.req('/api/report-vote',{'id':report['id'],'value':1},a)[0],400)
  self.assertEqual(self.req('/api/report-vote',{'id':report['id'],'value':1},b)[0],200)
  self.assertEqual(self.req('/api/report-vote',{'id':report['id'],'value':-1},b)[0],200)
  updated=next(r for r in self.req('/api/reports')[2] if r['id']==report['id'])
  self.assertEqual((updated['confirmations'],updated['cleared']),(0,1))
 def test_ticket_owner_and_admin_resolution(self):
  a=self.account('ticket');b=self.account('ticket-admin')
  self.assertEqual(self.req('/api/support',{'subject':'Map problem','body':'The road name is incorrect.'},a)[0],200)
  ticket=self.req('/api/support',cookie=a)[2][0]
  self.assertEqual(self.req('/api/support',cookie=b)[2],[])
  self.assertEqual(self.req('/api/admin',{'id':ticket['id'],'action':'resolve_ticket'},a)[0],403)
  with server.db() as c:c.execute("UPDATE users SET role='super_admin' WHERE email='ticket-admin@example.com'")
  self.assertEqual(self.req('/api/admin',{'id':ticket['id'],'action':'resolve_ticket'},b)[0],200)
  self.assertEqual(self.req('/api/support',cookie=a)[2][0]['status'],'resolved')
 def test_saved_place_edit_isolation_and_trip_validation(self):
  a=self.account('place-edit');b=self.account('place-other')
  self.req('/api/places',{'label':'Original','lat':6,'lon':3},a)
  place=self.req('/api/places',cookie=a)[2][0]
  self.req('/api/places',{**place,'label':'Other edit'},b)
  self.assertEqual(self.req('/api/places',cookie=a)[2][0]['label'],'Original')
  self.req('/api/places',{**place,'label':'Home'},a)
  self.assertEqual(self.req('/api/places',cookie=a)[2][0]['label'],'Home')
  self.assertEqual(self.req('/api/trips',{'label':'Past','lat':6,'lon':3,'arrival':'2020-01-01T00:00:00Z'},a)[0],400)
 def test_new_records_deleted_with_account(self):
  a=self.account('workflow-delete')
  self.req('/api/preferences',{'historyEnabled':True},a)
  self.req('/api/history',{'label':'Private','lat':6,'lon':3},a)
  self.req('/api/support',{'subject':'Private ticket','body':'Delete this ticket with account.'},a)
  self.req('/api/delete-account',{},a)
  with server.db() as c:
   self.assertEqual(c.execute("SELECT COUNT(*) FROM history WHERE label='Private'").fetchone()[0],0)
   self.assertEqual(c.execute("SELECT COUNT(*) FROM support_tickets WHERE subject='Private ticket'").fetchone()[0],0)
 def test_vehicle_provider_selection_and_avoidance_validation(self):
  previous={key:os.environ.get(key) for key in ('ROUTING_URL','MOTORCYCLE_ROUTING_URL','ROUTING_EXCLUDES','MOTORCYCLE_ROUTING_EXCLUDES')}
  original=server.upstream;calls=[];server.CACHE.clear()
  os.environ.update(ROUTING_URL='https://car.example',MOTORCYCLE_ROUTING_URL='https://motorcycle.example',ROUTING_EXCLUDES='toll,motorway',MOTORCYCLE_ROUTING_EXCLUDES='ferry')
  server.upstream=lambda url:calls.append(url) or {'code':'Ok','routes':[]}
  try:
   cap=self.req('/api/capabilities')[2]
   self.assertEqual(cap['routingVehicles'],['car','motorcycle'])
   self.assertEqual(self.req('/api/route?points=3,6;4,7&vehicle=motorcycle&avoid=ferry')[0],200)
   self.assertIn('https://motorcycle.example/route/',calls[-1]);self.assertIn('exclude=ferry',calls[-1])
   self.assertEqual(self.req('/api/route?points=3,6;4,7&vehicle=car&avoid=toll,motorway')[0],200)
   self.assertIn('exclude=motorway%2Ctoll',calls[-1])
   count=len(calls)
   self.assertEqual(self.req('/api/route?points=3,6;4,7&vehicle=car&avoid=ferry')[0],422)
   self.assertEqual(len(calls),count)
   self.assertEqual(self.req('/api/route?points=3,6;4,7&vehicle=plane')[0],400)
   os.environ.pop('MOTORCYCLE_ROUTING_URL')
   self.assertEqual(self.req('/api/route?points=3,6;4,7&vehicle=motorcycle')[0],503)
  finally:
   server.upstream=original;server.CACHE.clear()
   for key,value in previous.items():
    if value is None:os.environ.pop(key,None)
    else:os.environ[key]=value
 def test_mobile_assets_are_served(self):
  for path,marker in [('/map.html',b'/mobile.js'),('/mobile.js',b'prepareRoute'),('/mobile.css',b'--sheet-height')]:
   c=http.client.HTTPConnection('127.0.0.1',self.http.server_port);c.request('GET',path);response=c.getresponse()
   self.assertEqual(response.status,200);self.assertIn(marker,response.read());self.assertEqual(response.getheader('Cache-Control'),'no-cache');c.close()
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
