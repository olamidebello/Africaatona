import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import server
from deploy.configure_search import configure

class SearchTests(unittest.TestCase):
 def setUp(self):
  server.init();server.SEARCH_LAST=0
  with server.db() as c:c.execute('DELETE FROM search_cache')
 def test_photon_normalization_and_persistent_cache(self):
  calls=[]
  response={'features':[{'geometry':{'type':'Point','coordinates':[3.3792,6.5244]},'properties':{'name':'Lagos','city':'Lagos','country':'Nigeria'}}]}
  with patch.object(server,'upstream',side_effect=lambda url:calls.append(url) or response):
   result=server.geocode('https://photon.example','Lagos','photon')
   self.assertEqual(result,[{'lat':6.5244,'lon':3.3792,'display_name':'Lagos, Nigeria'}])
   self.assertEqual(server.geocode('https://photon.example','Lagos','photon'),result)
   self.assertEqual(len(calls),1)
   self.assertIn('/api/?q=Lagos',calls[0])
 def test_global_limit_and_concurrent_request_rejection(self):
  with patch.object(server,'upstream',return_value={'features':[]}):
   self.assertEqual(server.geocode('https://photon.example','First','photon'),[])
   self.assertIsNone(server.geocode('https://photon.example','Second','photon'))
   server.SEARCH_LAST=0;server.SEARCH_LOCK.acquire()
   try:self.assertIsNone(server.geocode('https://photon.example','Third','photon'))
   finally:server.SEARCH_LOCK.release()
 def test_existing_nominatim_provider_still_supported(self):
  with patch.object(server,'upstream',return_value=[{'lat':'6.5','lon':'3.3','display_name':'Lagos'}]) as fetch:
   self.assertEqual(server.geocode('https://private.example','Lagos','nominatim')[0]['lat'],6.5)
   self.assertIn('/search?q=Lagos',fetch.call_args.args[0])
 def test_invalid_provider_response_not_cached(self):
  with patch.object(server,'upstream',return_value={'unexpected':True}):
   with self.assertRaises(ValueError):server.geocode('https://photon.example','Lagos','photon')
  with server.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM search_cache').fetchone()[0],0)
 def test_configuration_preserves_private_provider_and_other_settings(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'service.env';p.write_text('PORT=8097\nROUTING_URL=http://127.0.0.1:5007\nGEOCODER_URL=https://private.example\n')
   before=p.read_text();self.assertFalse(configure(p)['changed']);self.assertEqual(p.read_text(),before)
 def test_empty_configuration_is_idempotent_and_protected(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'service.env';p.write_text('PORT=8097\nROUTING_URL=\nGEOCODER_URL=\n')
   self.assertTrue(configure(p)['changed']);self.assertFalse(configure(p)['changed'])
   self.assertIn('GEOCODER_URL=https://photon.komoot.io',p.read_text())
   self.assertIn('ROUTING_URL=\n',p.read_text());self.assertEqual(p.stat().st_mode & 0o777,0o600)
