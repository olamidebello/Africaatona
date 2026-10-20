"""Remove expired reports and sessions; rotate daily SQLite online backups."""
import sqlite3,time
from pathlib import Path
root=Path('/var/lib/africaatona'); source=sqlite3.connect(root/'atona.db')
with source:
 source.execute('DELETE FROM reports WHERE created<?',(time.time()-7200,))
 source.execute('DELETE FROM report_votes WHERE report_id NOT IN (SELECT id FROM reports)')
 source.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
backup=root/'backups';backup.mkdir(mode=0o700,exist_ok=True)
with sqlite3.connect(backup/(time.strftime('%Y-%m-%d')+'.db')) as target:source.backup(target)
for p in backup.glob('*.db'):
 if p.stat().st_mtime<time.time()-7*86400:p.unlink()
