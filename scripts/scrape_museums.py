"""Rebuild the sourced atlas from Wikipedia country and linked regional lists.
Run with Python + lxml. Caches raw responses outside the repository; preserves
source attribution and incomplete/failed fetches. No prose descriptions or photos
are copied. Imported records are directory candidates, not verified open venues.
"""
import concurrent.futures, csv, hashlib, json, os, re, time, unicodedata, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path(os.environ.get('MUSEUM_CACHE','/tmp/museum-scrape'));CACHE.mkdir(exist_ok=True)
OUT=ROOT/'dist'/'data';OUT.mkdir(exist_ok=True)
INDEX='https://en.wikipedia.org/wiki/Lists_of_museums'
DATE=datetime.now(timezone.utc).date().isoformat()
UA='MuseumOfMuseumsResearch/1.0 (educational directory; attributed list import)'
def clean(x):return re.sub(r'\s+',' ',re.sub(r'\[\s*\d+\s*\]','',x or '')).strip()
def norm(x):return re.sub(r'[^\w]','',unicodedata.normalize('NFKD',x).casefold())
def fetch(u):
 fn=CACHE/(u.rsplit('/',1)[-1]+'.html')
 if fn.exists():return fn.read_bytes()
 with urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u,safe=':/?=&%(),'),headers={'User-Agent':UA}),timeout=22) as r:b=r.read(8000000)
 fn.write_bytes(b);time.sleep(.18);return b

def valid_link(a,base):
 h=urllib.parse.urljoin(base,a.get('href',''))
 name=clean(a.text_content())
 if not name or len(name)>220:return None
 if any(x in h for x in ['#cite','/File:','/Help:','/Category:','/Template:','/Wikipedia:','/Special:','/List_of','/Lists_of']):return None
 if name.lower() in ['edit','website','official website','image','photo','coordinates','english','portuguese','german','french','japanese','spanish','chinese','in english','in french','in german','in japanese','in spanish','in portuguese']:return None
 if not h.startswith('https://en.wikipedia.org/wiki/'):return None
 return name,(None if 'redlink=1' in h else h.split('#')[0].split('?')[0])

def parse(u,country):
 started=time.time();status={'url':u,'country':country,'title':urllib.parse.unquote(u.rsplit('/',1)[-1]).replace('_',' '),'retrieved':DATE,'license':'CC BY-SA 4.0','records':0}
 try:
  raw=fetch(u);tree=html.fromstring(raw)
  content=tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," mw-parser-output ")]')
  if not content:status['status']='no_article_content';return [],[],status
  body=max(content,key=lambda e:len(e.text_content()))
  for el in body.xpath('.//*[contains(@class,"navbox") or contains(@class,"infobox") or contains(@class,"sidebar") or contains(@class,"toc") or contains(@class,"reflist") or contains(@class,"hatnote") or contains(@class,"metadata") or contains(@class,"sistersitebox") or contains(@class,"mw-editsection") or contains(@class,"reference")]'):
   if el.getparent() is not None:el.getparent().remove(el)
  children=[]
  for a in body.xpath('.//a[@href]'):
   href=urllib.parse.urljoin(u,a.get('href','')).split('#')[0].split('?')[0]
   if '/wiki/List_of_museums_in_' in href and 'redlink' not in a.get('href','') and href!=u:children.append(href)
  records=[];seen=set();headings={};skip=False
  def add(name,link,loc='',kind='',section=''):
   name=clean(name)
   if re.match(r'^(list of |province of )',name,re.I):return
   if len(name)<3 or len(name)>180 or name.lower() in ['name','museum','museums','institution','location','city','town','details','notes','see also','references','external links']:return
   key=link or norm(name)
   if key in seen:return
   seen.add(key)
   loc=clean(loc);kind=clean(kind)
   if len(loc)>110:loc=''
   if len(kind)>80:kind=''
   records.append({'name':name,'country':country,'locality':loc,'type':kind,'article':link,'sources':[u],'section':section[:120],'review':'directory import'})
  table_nodes=set()
  for el in body.iter():
   if el.tag in ['h2','h3','h4','h5']:
    level=int(el.tag[1]);headings={k:v for k,v in headings.items() if k<level};headings[level]=clean(el.text_content())
    skip=any(re.search(r'^(see also|references|notes|external links|bibliography|further reading|sources|footnotes|related|museum networks)',v,re.I) for v in headings.values())
   if skip:continue
   section=' / '.join(headings.values())
   if el.tag=='table':
    rows=el.xpath('./tr|./tbody/tr|./thead/tr')
    if len(rows)<2:continue
    header=[];hi=-1
    for ix,row in enumerate(rows[:4]):
     hs=row.xpath('./th|./td');texts=[clean(x.text_content()).lower() for x in hs]
     if any(x in ['name','museum','museum name','name of museum','name of the museum','institution','list of museums','english name'] for x in texts):header=texts;hi=ix;break
    if hi<0:continue
    ni=next((i for i,x in enumerate(header) if x in ['name','museum','museum name','name of museum','name of the museum','institution','list of museums','english name']),0)
    li=next((i for i,x in enumerate(header) if x in ['city','location','town/city','city/town','town','municipality','town / city','place']),None)
    ti=next((i for i,x in enumerate(header) if x in ['type','type of museum','specialisation','specialty','subject']),None)
    for row in rows[hi+1:]:
     cells=row.xpath('./td|./th')
     if len(cells)!=len(header):continue # ambiguous rowspans excluded
     cell=cells[ni];n=clean(cell.text_content());link=None
     anchors=cell.xpath('.//a[@href]')
     for a in anchors:
      val=valid_link(a,u)
      if val:n,link=val;break
     add(n,link,cells[li].text_content() if li is not None else '',cells[ti].text_content() if ti is not None else '',section)
   if el.tag=='li':
    if el.xpath('./ul|./ol') or el.xpath('ancestor::table|ancestor::nav'):continue
    ancestors=el.xpath('ancestor::*')
    if any(x.get('role')=='navigation' for x in ancestors):continue
    aa=el.xpath('./a[@href]|./b/a[@href]|./i/a[@href]|./span/a[@href]')
    val=None
    for a in aa:
     val=valid_link(a,u)
     if val:break
    if val:
     # First linked term must begin the list item; later links are often cities or citations.
     txt=clean(el.text_content());offset=txt.find(val[0])
     marker=r'\b(museum|musée|museo|museu|gallery|galleria|memorial|centre|center|collection)\b'
     lead=re.split(r'\s[–—-]\s|,|\s\(',txt)[0].strip()
     if offset>8:
      if re.search(marker,lead,re.I):add(lead,None,section=section)
      continue
     name,link=val
     # Names sometimes link the subject separately from "Museum".
     if re.search(marker,lead,re.I) and not re.search(marker,name,re.I) and len(lead)<150:
      name=lead;link=None
      for candidate in aa:
       v=valid_link(candidate,u)
       if v and re.search(marker,v[0],re.I):
        title=candidate.get('title','').replace(' (page does not exist)','')
        if title and norm(title)==norm(name):link=v[1]
     # Top-level city headings in nested country lists are not institutions.
     if 'by city' in section.lower() and not el.xpath('ancestor::li') and not re.search(marker,name,re.I):continue
     add(name,link,section=section)
    elif not aa:
     txt=clean(el.text_content());n=re.split(r'\s[–—-]\s',txt)[0]
     if re.search(r'\b(museum|musée|museo|museu)\b',n,re.I) and len(n)<100:add(n,None,section=section)
  status.update(status='ok',records=len(records),seconds=round(time.time()-started,1))
  return records,list(dict.fromkeys(children)),status
 except Exception as e:status.update(status='failed',error=str(e)[:200]);return [],[],status

def main():
 raw=fetch(INDEX);s=html.fromstring(raw);seeds={}
 for a in s.xpath('//a[@href]'):
  u=urllib.parse.urljoin(INDEX,a.get('href',''))
  if '/wiki/List_of_museums_in_' in u and 'redlink' not in u:
   c=clean(a.text_content());c={'Burma':'Myanmar','Czech Republic':'Czechia','Turkey':'Türkiye','Swaziland':'Eswatini','England':'United Kingdom','Scotland':'United Kingdom','Wales':'United Kingdom','Northern Ireland':'United Kingdom'}.get(c,c)
   seeds[u.split('#')[0]]=c
 allrecords=[];reports=[];subpages={}
 def batch(jobs):
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   futures={pool.submit(parse,u,c):(u,c) for u,c in jobs.items()}
   for fut in concurrent.futures.as_completed(futures):
    u,c=futures[fut];rows,children,report=fut.result();allrecords.extend(rows);reports.append(report)
    for x in children:
     if x not in seeds and x not in subpages:subpages[x]=c
    if len(reports)%10==0:print(f'{len(reports)} lists processed / {len(allrecords)} raw records',flush=True)
    (CACHE/'scrape-progress.json').write_text(json.dumps({'lists':len(reports),'rawRecords':len(allrecords)}))
 batch(seeds)
 # Exclude cross-country links and follow regional lists linked from country pages.
 regional=dict(list(subpages.items())[:300]);print(f'Country pass complete. {len(regional)} regional lists queued.',flush=True);batch(regional)
 extra={u:c for u,c in subpages.items() if u not in regional and u not in seeds}
 if extra:
  print(f'Following {len(extra)} further regional lists.',flush=True);batch(dict(list(extra.items())[:180]))
 merged={};namekeys={}
 for d in allrecords:
  nk=norm(d['name'])+'|'+d['country'];key=d['article'] or nk
  if nk in namekeys:key=namekeys[nk]
  namekeys[nk]=key
  if key in merged:
   old=merged[key];old['sources']=list(dict.fromkeys(old['sources']+d['sources']))
   for f in ['locality','type','article']:
    if not old[f] and d[f]:old[f]=d[f]
  else:merged[key]=d
 # Consolidate articles discovered when enriching initially unlinked records.
 final={}
 for d in merged.values():
  k=d['article'] or norm(d['name'])+'|'+d['country']
  if k in final:
   old=final[k];old['sources']=list(dict.fromkeys(old['sources']+d['sources']))
   for f in ['locality','type']:
    if not old[f]:old[f]=d[f]
  else:final[k]=d
 records=sorted(final.values(),key=lambda x:(x['name'].casefold(),x['country']))
 for d in records:d['id']='atlas-'+hashlib.sha1((d['article'] or d['name']+'|'+d['country']).encode()).hexdigest()[:12]
 # Report only populated lists as contributing sources, but retain every attempt.
 meta={'retrieved':DATE,'count':len(records),'countries':len(set(d['country'] for d in records)),'listsAttempted':len(reports),'contributingLists':sum(x['records']>0 for x in reports),'sourceFamily':'Wikipedia country and regional museum lists','index':INDEX,'license':'CC BY-SA 4.0','licenseUrl':'https://creativecommons.org/licenses/by-sa/4.0/','method':'Names, locations, and type labels extracted from list tables and bullet lists; deduplicated by article URL or normalized name within a country. No source descriptions or images copied. Imported venues have not been individually checked for current operation or museum status. Missing fields remain unknown. English-language list coverage is uneven.','sources':sorted(reports,key=lambda x:x['title'])}
 (OUT/'atlas.json').write_text(json.dumps(records,ensure_ascii=False,separators=(',',':')))
 (OUT/'sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 with (OUT/'atlas.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['name','country','locality','type','article','sources']);w.writeheader()
  for d in records:w.writerow({k:(' | '.join(d[k]) if isinstance(d[k],list) else d[k]) for k in w.fieldnames})
 (CACHE/'scrape-progress.json').unlink(missing_ok=True)
 print(json.dumps({k:v for k,v in meta.items() if k!='sources'}),flush=True)
if __name__=='__main__':main()
