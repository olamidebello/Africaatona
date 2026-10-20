import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from deploy.routing_only import configured,write_config,verify,capacity
class RoutingSetupTests(unittest.TestCase):
 def test_external_provider_validation(self):
  self.assertEqual(configured('https://routes.example/'),'https://routes.example')
  self.assertEqual(configured('http://127.0.0.1:5008'),'http://127.0.0.1:5008')
  for url in ['http://untrusted.example','https://routes.example\nPORT=1']:
   with self.assertRaises(ValueError):configured(url)
 def test_config_preserves_geocoder_and_protected_settings(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'service.env';p.write_text('PORT=8097\nGEOCODER_URL=https://photon.komoot.io\nROUTING_URL=\n')
   self.assertTrue(write_config('http://127.0.0.1:5008','Texas, United States',p))
   self.assertFalse(write_config('http://127.0.0.1:5008','Texas, United States',p))
   self.assertIn('GEOCODER_URL=https://photon.komoot.io',p.read_text())
   self.assertEqual(p.read_text().count('ROUTING_URL='),1);self.assertEqual(p.stat().st_mode & 0o777,0o600)
 def test_capacity_requires_available_memory_as_well_as_total(self):
  class Disk:free=40*1024**3
  with patch('deploy.routing_only.Path.read_text',return_value='MemTotal: 16777216 kB\nMemAvailable: 1048576 kB\n'),patch('deploy.routing_only.shutil.disk_usage',return_value=Disk()):
   self.assertFalse(capacity()['ready'])
