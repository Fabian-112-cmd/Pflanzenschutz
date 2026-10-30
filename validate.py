"""Validate atlas data and local assets without modifying files. Python 3, standard library only."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/diseases.json').read_text())
p=json.loads((root/'data/products.json').read_text())
c=json.loads((root/'data/credits.json').read_text())
ids=[x['id'] for x in d['diseases']]
assert len(ids)==len(set(ids)), 'Doppelte Schadbild-ID'
required={'peronospora','oidium','botrytis','schwarzfaeule','roter-brenner','esca','phomopsis','traubenwickler','kraeuselmilbe','pockenmilbe','rebzikaden','kirschessigfliege','reblaus','spinnmilben','magnesium','kalium','eisen','stickstoff','bor','trockenstress','sonnenbrand','frost','hagel','staunaesse','herbizidschaeden','schwarzholz','viruskrankheiten'}
assert required<=set(ids), 'Pflichtprofile fehlen'
for x in d['diseases']:
 for k in ['name','scientific','category','summary','organs','symptoms','cause','weather','confusions','prevention','bio','conventional','substances','sources']:assert x.get(k), (x['id'],k)
 assert x['category'] in ['pilze','schaedlinge','naehrstoffe','umwelt','sonstige']
 for s in x['sources']:assert s['url'].startswith('https://')
 for i in x['images']:
  assert (root/i['src']).is_file(), i['src']
  for k in ['caption','credit','license','source','organs']:assert i[k], (i['src'],k)
images=[i['src'] for x in d['diseases'] for i in x['images']]
assert sorted(images)==sorted(i['src'] for i in c['images']), 'Bildnachweise unvollständig'
for x in p['products']:
 assert x['modes'] and set(x['modes'])<=set(['bio','konventionell'])
 assert 'bio' not in x['modes'] or x['bioCandidate']
 assert set(x['diseaseIds'])<=set(ids)
 assert x['applications'] and x['source'].startswith('https://psm-zulassung.bvl.bund.de/')
 for a in x['applications']:
  assert a['area']=='Freiland'
  assert not any('Tafel' in u for u in a['use']) or any('Kelter' in u for u in a['use']),a['id']
  assert a['id'].startswith(x['id'])
  for r in a['rates']:assert r['unit'] or r['amount'] is None
manifest=json.loads((root/'manifest.webmanifest').read_text())
assert manifest['start_url']=='./' and manifest['scope']=='./' and manifest['id']=='./'
for i in manifest['icons']:assert (root/i['src']).is_file()
print(f"OK: {len(ids)} Profile, {len(images)} Bilder, {len(p['products'])} Produkte, {sum(len(x['applications']) for x in p['products'])} Anwendungen")
print('Ohne eingebundene Fotos: '+', '.join(x['name'] for x in d['diseases'] if not x['images']))
