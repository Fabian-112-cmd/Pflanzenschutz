"""Öffentliche Originalmeldungen einsammeln; keine Spritzempfehlungen erzeugen.

Keine API-Schlüssel. Bei Fehlern bleiben bekannte Meldungen erhalten und die
betroffene Quelle wird ausdrücklich als unvollständig gekennzeichnet.
"""
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/rebschutz.json'
SOURCES = [
 {'id': 'dlr', 'name': 'DLR Rheinland-Pfalz · Weinbau', 'kind': 'rss',
  'url': 'https://www.dlr.rlp.de/Internet/global/SitRSSFeeds.nsf/rss?openagent&uid=F3997406474A7B72C12578A1004C5401',
  'home': 'https://www.dlr-rheinpfalz.rlp.de/'},
 {'id': 'dlr-bio', 'name': 'DLR Rheinland-Pfalz · Ökoweinbau', 'kind': 'rss',
  'url': 'https://www.dlr.rlp.de/Internet/global/SitRSSFeeds.nsf/rss?openagent&uid=E5254982E32D208AC12586CB002289C4',
  'home': 'https://www.oekolandbau.rlp.de/'},
 {'id': 'psinfo', 'name': 'PS Info Weinbau · DLR Rheinpfalz', 'kind': 'rss',
  'url': 'https://weinbau.pflanzenschutz-information.de/rss',
  'home': 'https://weinbau.pflanzenschutz-information.de/'},
 {'id': 'bvl', 'name': 'BVL · Fachmeldungen', 'kind': 'bvl',
  'url': 'https://www.bvl.bund.de/DE/Aktuelles/Fachmeldungen/fachmeldungen_node.html?cms_bereich=Pflanzenschutzmittel&resultsPerPage=100&cms_thema=Fachmeldungen',
  'home': 'https://www.bvl.bund.de/DE/Arbeitsbereiche/04_Pflanzenschutzmittel/psm_node.html'},
]

def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', value or ''))).strip()

def official(url):
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or '').lower()
    return u.scheme == 'https' and not u.username and not u.password and (
        host == 'bvl.bund.de' or host.endswith('.bvl.bund.de') or
        host == 'pflanzenschutz-information.de' or host.endswith('.pflanzenschutz-information.de') or
        host in ('www.dlr.rlp.de', 'www.dlr-rheinpfalz.rlp.de', 'www.weinbau.rlp.de',
                 'www.pflanzenschutz.rlp.de', 'www.oekolandbau.rlp.de'))

def fetch(url):
    if not official(url):
        raise ValueError('Nicht freigegebene Fachquelle')
    request = urllib.request.Request(url, headers={'User-Agent': 'Weingut-Rebschutz/1.0 (public source reader)'})
    with urllib.request.urlopen(request, timeout=25) as response:
        if not official(response.url):
            raise ValueError('Weiterleitung außerhalb der Fachquellen')
        raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError('Quelle zu groß')
        return raw

def published(value):
    try:
        return email.utils.parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError, AttributeError):
        try:
            return dt.date.fromisoformat(value[:10]).isoformat()
        except (TypeError, ValueError):
            return None

def relevant(source, title, body, names=()):
    text = (title + ' ' + body).lower()
    plant = bool(re.search(r'rebschutz|pflanzenschutz|peronospora|oidium|botrytis|schwarzfäule|esca|traubenwickler|reblaus|zikad|milben|kirschessigfliege|zulassung|widerruf|aufbrauch|notfallzulassung|frost|hagel|sonnenbrand', text))
    if not plant:
        return False
    if source['id'].startswith('dlr'):
        # Keine regionalen Situationsmeldungen aus Mosel, Nahe usw. als Pfalz-Warnung.
        if re.search(r'\b(mosel|rheinhessen|ahr|nahe|mittelrhein)\b', title.lower()) and not re.search(r'pfalz|landesweit', title.lower()):
            return False
        return bool(re.search(r'pfalz|rheinpfalz|landesweit|rheinland-pfalz', text))
    if source['id'] == 'psinfo':
        return True  # Offiziell auf Weinbau gefilterter RSS-Endpunkt.
    return bool(re.search(r'weinreb|weinbau|keltertraub|rebschutz|traubenwickler|reblaus', text) or
                any(re.search(r'(?<!\w)' + re.escape(n) + r'(?!\w)', text) for n in names) or
                re.search(r'(aufzeichnungs|dokumentations)pflicht.*pflanzenschutz|pflanzenschutz.*(aufzeichnungs|dokumentations)pflicht', text))

def item(source, title, body, url, day, today):
    if not official(url) or not day or not (today-dt.timedelta(days=90) <= dt.date.fromisoformat(day) <= today):
        return None
    lower = (title + ' ' + body).lower()
    modes = ['bio'] if source['id']=='dlr-bio' or re.search(r'\bökoweinbau\b|\bökologischer weinbau\b', title.lower()) else ['bio', 'konventionell']
    legal = bool(re.search(r'zulassung|widerruf|aufbrauch|anwendungsbestimmung|abverkauf|notfall', lower))
    impact = ('Vor dem nächsten Einsatz die betroffenen Weinbau-Anwendungen, Fristen und Auflagen in der Originalmeldung prüfen.' if legal else
              'Die neue Fachmeldung mit Entwicklungsstand und Befall im eigenen Wingert abgleichen; konkrete Maßnahmen der Originalquelle entnehmen.')
    # Titel ist das einzige übernommene Textzitat (maximal 24 Wörter).
    short_title = ' '.join(clean(title).split()[:24])
    return {'id': hashlib.sha256((url+'|'+day+'|'+clean(title)+'|'+clean(body)).encode()).hexdigest()[:24],
            'sourceId': source['id'], 'source': source['name'], 'title': short_title,
            'publishedAt': day, 'url': url, 'modes': modes,
            'category': 'Zulassung & Fristen' if legal else 'Rebschutz & Schadbilder',
            'impact': impact, 'bioStatus': 'BIO-Anwendbarkeit gesondert anhand der aktuellen Öko-Vorgaben prüfen.',
            'modeNote': 'Allgemeine Fachinformation; die Zuordnung ist keine Zulassungs- oder BIO-Freigabe.'}

def rss(source, today, names=()):
    root = ET.fromstring(fetch(source['url']))
    if root.tag.rsplit('}',1)[-1] not in ('rss', 'feed'):
        raise ValueError('Keine RSS-/Atom-Antwort')
    result=[]
    for entry in root.findall('.//item') + root.findall('{http://www.w3.org/2005/Atom}entry'):
        def field(key):
            e=entry.find(key)
            if e is None:
                e=entry.find('{http://www.w3.org/2005/Atom}'+key)
            return e
        def text(key):
            e=field(key)
            return ''.join(e.itertext()) if e is not None else ''
        title,body=text('title'),text('description') or text('summary')
        link=field('link');url=(link.get('href') or link.text or '') if link is not None else ''
        day=published(text('pubDate') or text('published') or text('updated'))
        # Bei DLR kann pubDate das Einstelldatum sein. Das ausdrücklich im
        # Mitteilungstitel genannte Dokumentdatum hat für die Anzeige Vorrang.
        if source['id'].startswith('dlr'):
            stated=re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b',clean(title))
            if stated:
                try: day=dt.datetime.strptime(stated[1],'%d.%m.%Y').date().isoformat()
                except ValueError: pass
        if relevant(source,title,body,names):
            row=item(source,title,body,url.strip(),day,today)
            if row: result.append(row)
    return result

def bvl(source, today, names=()):
    page=fetch(source['url']).decode('utf-8')
    # Auf offiziellen Listeneinträgen steht das Veröffentlichungsdatum separat.
    blocks=re.findall(r'<(?:article|li)\b[^>]*class="[^"]*c-pressrelease[^\"]*"[^>]*>(.*?)</(?:article|li)>',page,re.S)
    if not blocks:
        # Aktuelles BVL-Markup nutzt c-pressrelease als div.
        blocks=re.split(r'(?=<[^>]*class="c-pressrelease(?:\s|"))',page)[1:]
    if not blocks:
        raise ValueError('BVL-Listenformat nicht erkannt')
    result=[]
    for block in blocks[:100]:
        link=re.search(r'href="([^"]*/SharedDocs/Fachmeldungen/04_pflanzenschutzmittel/[^"]+)"',block)
        day=re.search(r'c-pressrelease__date[^>]*>.*?(\d{2}\.\d{2}\.\d{4})',block,re.S)
        title=re.search(r'<h[23][^>]*>(.*?)</h[23]>',block,re.S)
        if not (link and day and title):continue
        date=dt.datetime.strptime(day[1],'%d.%m.%Y').date()
        if not today-dt.timedelta(days=30)<=date<=today:continue
        url=html.unescape(link[1]);body=clean(fetch(url).decode('utf-8'))
        title=clean(title[1])
        if relevant(source,title,body,names):
            row=item(source,title,body,url,date.isoformat(),today)
            if row:result.append(row)
    return result

def update():
    now=dt.datetime.now(dt.timezone.utc);today=now.date();stamp=now.isoformat()
    old=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {'items':[], 'sources':[]}
    old_sources={s['id']:s for s in old.get('sources',[])}
    names=[]
    catalog=ROOT/'data/products.json'
    if catalog.exists():
        for p in json.loads(catalog.read_text()).get('products',[]):
            names.extend(n.lower() for n in [p.get('name','')]+[s.get('name','') for s in p.get('substances',[])] if len(n)>=5)
    records={x['url']:x for x in old.get('items',[]) if today-dt.timedelta(days=90)<=dt.date.fromisoformat(x['publishedAt'])<=today}
    statuses=[]
    def run(source):
        try:return source,(rss if source['kind']=='rss' else bvl)(source,today,names),None
        except Exception as e:return source,[],type(e).__name__+': '+str(e)[:160]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for source,rows,error in pool.map(run,SOURCES):
            status={k:source[k] for k in ('id','name','home')};status.update({'checkedAt':stamp,'ok':error is None,
                'lastSuccessAt':stamp if error is None else old_sources.get(source['id'],{}).get('lastSuccessAt'),
                'error':error})
            statuses.append(status)
            for row in rows:
                prior=records.get(row['url'])
                row['firstSeenAt']=prior.get('firstSeenAt',stamp) if prior else stamp
                records[row['url']]=row
            print(source['id'], 'OK: '+str(len(rows)) if error is None else 'UNVOLLSTÄNDIG: '+error)
    payload={'schemaVersion':1,'generatedAt':stamp,'coverage':'Öffentlich verfügbare DLR-/PS-Info-Meldungen und BVL-Fachmeldungen. Kein Zugriff auf kostenpflichtige Informationsdienste; keine Vollständigkeitsgarantie.',
             'sources':statuses,'items':sorted(records.values(),key=lambda x:x['publishedAt'],reverse=True)[:200]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    pending=OUTPUT.with_suffix('.pending');pending.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');pending.replace(OUTPUT)
    # Nicht vor dem Speichern abbrechen: Abruffehler müssen in der App sichtbar werden.
    return all(s['ok'] for s in statuses)

if __name__=='__main__':
    update()
