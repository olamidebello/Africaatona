#!/usr/bin/env python3
"""Create or explicitly promote the operator account; credentials stay root-only."""
import importlib.util,json,os,secrets,sqlite3,sys
from pathlib import Path
root=Path('/opt/africaatona');os.environ['ATONA_DATA']='/var/lib/africaatona'
spec=importlib.util.spec_from_file_location('atona',root/'server.py');server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server);server.init()
credentials=Path('/var/lib/africaatona-admin/credentials.json');credentials.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
email=os.getenv('ATONA_ADMIN_EMAIL','dobcalldemo@gmail.com').lower()
with server.db() as c:
 row=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
 if row:c.execute("UPDATE users SET role='super_admin' WHERE id=?",(row[0],))
 else:
  pw=secrets.token_urlsafe(24);salt=secrets.token_hex(16)
  c.execute("INSERT INTO users(email,name,salt,password,role) VALUES(?,?,?,?,?)",(email,'Administrator',salt,server.password(pw,salt),'super_admin'))
  credentials.write_text(json.dumps({'email':email,'password':pw}));credentials.chmod(0o600)
print('Administrator configured. New credentials, if generated, are in /var/lib/africaatona-admin/credentials.json')
