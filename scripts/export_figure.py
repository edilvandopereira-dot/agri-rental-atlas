"""Export an editorial figure from the validated public market snapshot."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/processed/market.json').read_text())
national=next(r for r in d['national'] if r['year']==2024)
rows={r['state_id']:r for r in d['states'] if r['year']==2024}
total=sum(national['crop_area_ha'].values());focus=rows['51']
ink,teal,copper,paper,muted='#10293D','#007E84','#C26642','#F4F0E8','#596C77'
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':ink,'svg.fonttype':'none'})
fig=plt.figure(figsize=(10,11.25),dpi=120,facecolor=paper)
fig.text(.07,.948,'EDILVANDO EUFRAZIO     /     APPLIED DATA SCIENCE',fontsize=10,color=teal,weight='bold')
fig.text(.07,.888,'Where would you\ninvestigate next?',fontsize=34,weight='bold',va='top',linespacing=1.18)
fig.text(.07,.754,'Agricultural machinery rental without operator · Brazil, 2024',fontsize=12,color=muted)
fig.text(.07,.727,'Crop footprint: soybeans, corn, sugar cane and cotton.',fontsize=10,color=muted)
fig.text(.07,.699,'MATO GROSSO',fontsize=11,color=teal,weight='bold')
fig.text(.07,.633,f"{100*sum(focus['crop_area_ha'].values())/total:.1f}%",fontsize=37,color=teal,weight='bold')
fig.text(.07,.598,'of Brazil’s selected crop footprint',fontsize=11,color=muted)
fig.text(.55,.633,f"{100*focus['rental_sites']/national['rental_sites']:.1f}%",fontsize=37,color=copper,weight='bold')
fig.text(.55,.598,'of rental establishments',fontsize=11,color=muted)
ax=fig.add_axes([.065,.185,.60,.36],facecolor=paper)
geo=json.loads((ROOT/'data/raw/brazil_states.geojson').read_text())
for feature in geo['features']:
    sid=feature['properties']['codarea'];r=rows[sid];gap=100*(sum(r['crop_area_ha'].values())/total-r['rental_sites']/national['rental_sites'])
    color='#A04D2B' if gap>10 else copper if gap>3 else '#E6B79E' if gap>1 else teal if gap< -5 else '#8DB9B3' if gap< -1 else '#E5DED0'
    g=feature['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    for polygon in polys:ax.add_patch(Polygon(polygon[0],closed=True,facecolor=color,edgecolor=ink if sid=='51' else paper,linewidth=1.5 if sid=='51' else .7))
ax.set_xlim(-74,-34);ax.set_ylim(-34,6);ax.set_aspect('equal');ax.axis('off')
for x,y,label in [(-56,-13,'MT'),(-45,-18,'MG'),(-51,-24,'PR')]:ax.text(x,y,label,ha='center',va='center',fontsize=11,weight='bold',color=ink,bbox={'facecolor':paper,'edgecolor':'none','pad':2,'alpha':.9})
fig.text(.69,.493,'267',fontsize=27,weight='bold');fig.text(.69,.467,'rental establishments',fontsize=10,color=muted)
fig.text(.69,.405,'21.17M ha',fontsize=22,weight='bold');fig.text(.69,.379,'selected crop area',fontsize=10,color=muted)
fig.text(.69,.302,'A commercial\nresearch question,\nnot proof of\nunmet demand.',fontsize=12,color=ink,linespacing=1.6,va='top')
fig.legend(handles=[Patch(color=teal,label='More rental share'),Patch(color='#E5DED0',label='Near balance'),Patch(color=copper,label='More crop share')],loc='lower left',bbox_to_anchor=(.07,.145),ncol=3,frameon=False,fontsize=9)
fig.text(.07,.105,'Map: selected crop-area share minus rental-establishment share.\nCheck own fleets, operators and cross-state service before acting.',fontsize=10,color=ink,linespacing=1.5)
fig.text(.07,.037,'SOURCE  IBGE CEMPRE 9528 · PAM 1612 · CNAE 77.31-4 · Reference: 2024\nCrops: soybeans, corn, sugar cane, cotton. Planted area can repeat land; rental serves other uses.',fontsize=8.5,color=muted,linespacing=1.6)
for ext in ['png','svg']:fig.savefig(ROOT/f'assets/rental-geography-2024.{ext}',facecolor=paper)
print('Exported 1200×1350 figure from validated aggregates')
