"""Validate pinned IBGE aggregates and build a transparent commercial screen."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
CROPS={'2689':'Cotton','2696':'Sugar cane','2711':'Corn','2713':'Soybeans'}
YEARS=(2022,2023,2024)


def number(value):
    if value=='-':return 0
    if value in ('...', '..', 'X', 'x', '', None):return None
    result=float(value)
    if not math.isfinite(result) or result<0:raise ValueError(f'Invalid value: {value}')
    return int(result) if result.is_integer() else result


def parse(filename, allowed_variables, category_ids):
    variables=json.loads((ROOT/'data/raw'/filename).read_text())
    if {v['id'] for v in variables}!=set(allowed_variables):raise ValueError('Unexpected variables')
    rows=[]; seen=set()
    for variable in variables:
        for result in variable['resultados']:
            classification=result['classificacoes'][0]
            categories=classification['categoria']
            if len(categories)!=1 or not set(categories).issubset(category_ids):raise ValueError('Unexpected category')
            category=next(iter(categories))
            for series in result['series']:
                sid=series['localidade']['id']
                for year,raw in series['serie'].items():
                    key=(sid,int(year),variable['id'],category)
                    if int(year) not in YEARS or key in seen:raise ValueError('Unexpected year or duplicate key')
                    seen.add(key)
                    rows.append({'state_id':sid,'year':int(year),'variable':variable['id'],
                                 'category':category,'value':number(raw),'raw_value':raw})
    return rows


def safe_ratio(numerator, denominator):
    return numerator/denominator if numerator is not None and denominator is not None and denominator>0 else None


def reconcile(rows, national, variable, category):
    checks=[]
    for year in YEARS:
        values=[r['value'] for r in rows if r['year']==year and r['variable']==variable and r['category']==category]
        expected=next(r['value'] for r in national if r['year']==year and r['variable']==variable and r['category']==category)
        known=sum(v for v in values if v is not None);missing=sum(v is None for v in values)
        passed=(len(values)==27 and expected is not None and (known==expected if not missing else known<=expected))
        checks.append({'year':year,'variable':variable,'category':category,'states':len(values),
                       'known_sum':known,'national':expected,'missing_states':missing,
                       'type':'exact' if not missing else 'known subtotal only','passed':passed})
    return checks


def make_map(geo):
    paths=[]
    def point(xy):return ((xy[0]+74)*12, (6-xy[1])*12)
    for feature in geo['features']:
        geometry=feature['geometry']; polys=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        commands=[];largest=[]
        for polygon in polys:
            if len(polygon[0])>len(largest):largest=polygon[0]
            for ring in polygon:
                pts=[point(xy) for xy in ring]
                commands.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)+'Z')
        pts=[point(xy) for xy in largest]
        sid=feature['properties']['codarea']
        paths.append({'id':sid,'d':''.join(commands),
                      'label_x':(min(p[0] for p in pts)+max(p[0] for p in pts))/2,
                      'label_y':(min(p[1] for p in pts)+max(p[1] for p in pts))/2})
    return paths


def build():
    raw=ROOT/'data/raw'; manifest=json.loads((raw/'manifest.json').read_text())
    for f in manifest['files']:
        if hashlib.sha256((raw/f['file']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Source hash mismatch')
    rental=parse('rental_states.json',{'706','707'},{'117725'})
    rental_br=parse('rental_brazil.json',{'706','707'},{'117725'})
    crop=parse('crop_states.json',{'109'},set(CROPS))
    crop_br=parse('crop_brazil.json',{'109'},set(CROPS))
    firms=parse('companies_brazil.json',{'2585'},{'117725'})
    states=json.loads((raw/'states.json').read_text())
    ids={str(s['id']) for s in states}
    if len(ids)!=27 or {r['state_id'] for r in rental}!=ids or {r['state_id'] for r in crop}!=ids:raise ValueError('State coverage mismatch')
    if len(rental)!=162 or len(crop)!=324:raise ValueError('Incomplete state-year-variable grid')
    checks=reconcile(rental,rental_br,'706','117725')+reconcile(rental,rental_br,'707','117725')
    for category in CROPS:checks+=reconcile(crop,crop_br,'109',category)
    if not all(c['passed'] for c in checks):raise ValueError('National reconciliation failed')
    values={(r['state_id'],r['year'],r['variable'],r['category']):r['value'] for r in rental+crop}
    br={(r['year'],r['variable'],r['category']):r['value'] for r in rental_br+crop_br+firms}
    rows=[]
    for state in sorted(states,key=lambda s:s['id']):
        sid=str(state['id'])
        for year in YEARS:
            rows.append({'state_id':sid,'state':state['nome'],'abbr':state['sigla'],
                         'region':state['regiao']['nome'],'year':year,
                         'rental_sites':values[(sid,year,'706','117725')],
                         'employment':values[(sid,year,'707','117725')],
                         'crop_area_ha':{c:values[(sid,year,'109',c)] for c in CROPS}})
    national=[{'year':y,'rental_sites':br[(y,'706','117725')],'rental_companies':br[(y,'2585','117725')],
               'employment':br[(y,'707','117725')], 'crop_area_ha':{c:br[(y,'109',c)] for c in CROPS}} for y in YEARS]
    geo=json.loads((raw/'brazil_states.geojson').read_text())
    if {f['properties']['codarea'] for f in geo['features']}!=ids:raise ValueError('Geometry coverage mismatch')
    payload={'years':YEARS,'crops':CROPS,'states':rows,'national':national,'map':make_map(geo),
             'sources':manifest,'scope':'CNAE 77.31-4: agricultural machinery rental without operator. Crop footprint covers selected crops only.'}
    out=ROOT/'data/processed';out.mkdir(exist_ok=True)
    (out/'market.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    qa={'passed':True,'source_hashes_verified':len(manifest['files']),'state_years':len(rows),
        'crop_state_years':len(crop),'reconciliations':checks,'map_states':len(geo['features']),
        'raw_symbol_counts':{symbol:sum(r['raw_value']==symbol for r in rental+crop) for symbol in ['-','X','...','..']}}
    (ROOT/'data/qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    dbpath=out/'market.sqlite';db=sqlite3.connect(dbpath)
    db.executescript('DROP TABLE IF EXISTS rental; DROP TABLE IF EXISTS crops; CREATE TABLE rental(state_id TEXT,year INTEGER,sites INTEGER,employment INTEGER,PRIMARY KEY(state_id,year)); CREATE TABLE crops(state_id TEXT,year INTEGER,crop TEXT,planted_ha REAL,PRIMARY KEY(state_id,year,crop));')
    db.executemany('INSERT INTO rental VALUES (?,?,?,?)',[(r['state_id'],r['year'],r['rental_sites'],r['employment']) for r in rows])
    db.executemany('INSERT INTO crops VALUES (?,?,?,?)',[(r['state_id'],r['year'],c,v) for r in rows for c,v in r['crop_area_ha'].items()]);db.commit();db.close()
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['state_id','state','abbr','year','rental_local_units','employment']+['planted_ha_'+CROPS[c].replace(' ','_').lower() for c in CROPS])
    for r in rows:writer.writerow([r['state_id'],r['state'],r['abbr'],r['year'],r['rental_sites'],r['employment']]+[r['crop_area_ha'][c] for c in CROPS])
    (out/'state_year_base.csv').write_text(output.getvalue())
    template=(ROOT/'web/template.html').read_text();content=template.replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')).replace('__CHARTJS__',(ROOT/'vendor/chart.umd.min.js').read_text()).replace('__CSS__',(ROOT/'web/style.css').read_text()).replace('__JS__',(ROOT/'web/app.js').read_text()).replace('__I18N__',json.dumps(json.loads((ROOT/'web/i18n.json').read_text()),ensure_ascii=False).replace('</','<\\/')).replace('__MODELS__',(ROOT/'web/models.js').read_text())
    (ROOT/'docs/index.html').write_text(content)
    print(json.dumps({'validated':True,'state_year_rows':len(rows),'reconciliation_checks':len(checks),'national_2024':national[-1]},ensure_ascii=False))
    return payload


if __name__=='__main__':build()
