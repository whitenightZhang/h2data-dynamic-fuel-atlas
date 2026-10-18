from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import cartopy.crs as ccrs
import cartopy.feature as cf
import fitz
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'Fig2_Original_Maps_Revised_GHI_20260914/source_data'
sys.path.insert(0,str(ROOT.parent/'Fig2_Original_Maps_Revised_GHI_20260914'))
from audit_panel_alignment import require_matplotlib_panel_alignment
SOURCE=OLD/'H2_paired_costs_all_locations.csv.gz'
d=pd.read_csv(SOURCE,low_memory=False)
assert len(d)==684229 and not d.duplicated(['year','latitude','longitude']).any()
assert np.isfinite(d[['static_cost_per_kg','hourly8760_cost_per_kg']]).all().all()
years=[2030,2035,2050]
TARGETS={2030:2.0,2035:2.0,2050:2.0}
BLUE='#5E929F'; AMBER='#DEAB67'; GREY='#E5E8EA'; PURPLE='#987BA8'; INK='#242A2E'
COLORS=[GREY,BLUE,AMBER,PURPLE]
NAMES=['Neither meets','Both meet','Annual-average only','Hourly only']
def cats(g,t):
 s=g.static_cost_per_kg.to_numpy()<=t; h=g.hourly8760_cost_per_kg.to_numpy()<=t
 return np.where(s&h,1,np.where(s&~h,2,np.where(~s&h,3,0)))
def stats(g,t):
 v=cats(g,t); counts=np.bincount(v,minlength=4); assert counts.sum()==len(g)
 return dict(n=len(g),**{f'cat{k}_n':int(counts[k]) for k in range(4)},**{f'cat{k}_pct':float(counts[k]/len(g)*100) for k in range(4)})
regional=[]; globalrows=[]
for y,g in d.groupby('year'):
 for t in [TARGETS[int(y)]]:
  globalrows.append(dict(year=int(y),target_usd_kg=t,**stats(g,t)))
  for name,r in g.groupby('region_name',dropna=False):
   regional.append(dict(year=int(y),target_usd_kg=t,region_name=name,**stats(r,t)))
reg=pd.DataFrame(regional); glob=pd.DataFrame(globalrows)
reg.to_csv(ROOT/'source_data/regional_target_classification.csv',index=False)
glob.to_csv(ROOT/'source_data/global_target_classification.csv',index=False)
labels={'Africa_N':'North Africa','Africa_S':'Southern Africa','Africa_E':'East Africa','Africa_W':'West Africa','Europe_Eastern':'Eastern Europe','Europe_Non_EU':'Other Europe','South America_S':'S. South America','South America_N':'N. S. America','Australia_NZ':'Australia / NZ','Central America':'Central America','Southeast Asia':'SE Asia','European FTA':'European FTA'}
med=d[~d.region_name.isin(['Unknown','#N/A'])].groupby(['year','region_name'],observed=True).agg(hourly_median=('hourly8760_cost_per_kg','median'),static_median=('static_cost_per_kg','median'),locations=('latitude','size')).reset_index()
order=med[med.year==2035].sort_values(['hourly_median','region_name']).region_name.tolist()[:10]
fixed=med[med.region_name.isin(order)].copy();fixed['region_order']=fixed.region_name.map({name:i for i,name in enumerate(order)})
fixed.sort_values(['year','region_order']).to_csv(ROOT/'source_data/fixed_region_cost_pairs.csv',index=False)
med.to_csv(ROOT/'source_data/all_regional_cost_medians.csv',index=False)
original=fitz.open(OLD/'Original_Figure_2.pdf'); W,H=original[0].rect.width,original[0].rect.height
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial'],'font.size':6.5,'axes.labelsize':6.2,'xtick.labelsize':6,'ytick.labelsize':6,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.5,'xtick.major.width':.5,'xtick.major.size':2,'ytick.major.size':0,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'figure.facecolor':'white','savefig.facecolor':'white','legend.frameon':False})
fig=plt.figure(figsize=(W/72,H/72),dpi=300)
def axpt(x,top,w,h,name,projection=None):
 return fig.add_axes([x/W,(H-top-h)/H,w/W,h/H],label=name,projection=projection)
def txt(x,top,s,**kw):return fig.text(x/W,1-top/H,s,**kw)
def title(x,top,letter,s):
 txt(x,top,letter,fontsize=8,fontweight='bold',va='top');txt(x+12,top,s,fontsize=7,va='top')
# Replace display text while retaining the original map and color-bar artwork.
updated_label_rects=[]; updated_label_artists=[]
def replace_original_label(spans,replacement,center=False):
 rect=fitz.Rect(spans[0]['bbox'])
 for span in spans[1:]: rect.include_rect(fitz.Rect(span['bbox']))
 updated_label_rects.append(rect)
 first=spans[0]
 x=(rect.x0+rect.x1)/2 if center else first['origin'][0]
 color=tuple(((first['color']>>shift)&255)/255 for shift in [16,8,0])
 updated_label_artists.append(txt(x,first['origin'][1],replacement,fontsize=first['size'],color=color,ha='center' if center else 'left',va='baseline'))
for block in original[0].get_text('dict')['blocks']:
 if 'lines' not in block: continue
 spans=[span for line in block['lines'] for span in line['spans'] if span['bbox'][0]<191]
 if not spans: continue
 titles=[span for span in spans if '8760-hour cost' in span['text']]
 for span in titles: replace_original_label([span],span['text'].replace('8760-hour','Hourly'))
 medians=[span for span in spans if span['text'].startswith('median ')]
 if medians:
  assert len(medians)==1 and len(spans)==2
  median_spans=[dict(span) for span in spans]
  median_spans[0]['origin']=(100.,medians[0]['origin'][1]-7.06905)
  replace_original_label(median_spans,medians[0]['text'].replace('USD kg','USD/kg'))
 if any('8760-hour LCOH' in span['text'] for span in spans):
  replace_original_label(spans,'Hourly LCOH (USD/kg)',center=True)
assert len(updated_label_artists)==7
axes=[]
for j,y in enumerate(years):
 t=TARGETS[y]; top=15.2+114.21*j; name=chr(68+j); title(202,5.6+114.21*j,name,f'{y}  |  Low-cost classification')
 ax=axpt(202,top,160,80,name,ccrs.PlateCarree());axes.append(ax)
 ax.set_extent([-180,180,-90,90],crs=ccrs.PlateCarree())
 ax.add_feature(cf.LAND.with_scale('110m'),facecolor='#F6F7F7',edgecolor='none',zorder=0)
 g=d[d.year==y]; c=cats(g,t)
 # Use every paired location; rasterized point layer, vector axes and labels.
 for k in [0,1,2,3]:
  mask=c==k
  ax.scatter(g.loc[mask,'longitude'],g.loc[mask,'latitude'],s=.33,c=COLORS[k],marker='s',edgecolors='none',rasterized=True,transform=ccrs.PlateCarree(),zorder=1+k*.1)
 ax.coastlines('110m',linewidth=.25,color='#90989C',zorder=3)
 ax.set_xticks([-120,-60,0,60,120,180],crs=ccrs.PlateCarree());ax.set_xticklabels(['120°W','60°W','0°','60°E','120°E','180°'],fontsize=6)
 ax.set_yticks([],crs=ccrs.PlateCarree())
 ax.spines['geo'].set_linewidth(.5)
 val=glob[(glob.year==y)&(glob.target_usd_kg==t)].iloc[0].cat2_pct
 txt(204,top+91,f'Annual-average only: {val:.1f}%',fontsize=5.8,va='top')
for j,y in enumerate(years):
 letter=chr(71+j);top=5.6+114.21*j
 title(377,top,letter,f'{y}  |  Regional costs')
 r=fixed[fixed.year==y].set_index('region_name').loc[order].reset_index()
 ax=axpt(432,top+20,87,72,letter);axes.append(ax)
 for yy,row in r.iterrows():
  ax.plot([row.static_median,row.hourly_median],[yy,yy],color='#A9B3B9',linewidth=.7,zorder=1)
 ax.axvline(2,color='#646D72',lw=.7,ls=(0,(3,2)),zorder=0)
 ax.scatter(r.static_median,np.arange(10),s=12,color=AMBER,edgecolors='none',zorder=3)
 ax.scatter(r.hourly_median,np.arange(10),s=12,color=BLUE,edgecolors='none',zorder=3)
 ax.set_yticks(np.arange(10),[labels.get(x,x) for x in order],fontsize=5.8);ax.tick_params(axis='y',pad=3)
 ax.set_ylim(9.65,-.65);ax.set_xlim(.75,3.05);ax.set_xticks([1,2,3]);ax.set_xlabel('Median LCOH (USD/kg)',labelpad=2);ax.spines['left'].set_visible(False)
# One shared legend for all paired classification maps and regional panels.
for i,k in enumerate([1,2,0,3]):
 top=348+i*8.3
 fig.add_artist(plt.Rectangle((204/W,1-(top+5)/H),5/W,5/H,transform=fig.transFigure,color=COLORS[k],ec='none'))
 txt(213,top-1,NAMES[k],fontsize=6.2,va='top')
for x,c,label in [(382,AMBER,'Annual-average'),(466,BLUE,'Hourly')]:
 fig.add_artist(plt.Line2D([x/W],[1-352/H],marker='o',ms=3.6,color=c,linestyle='none',transform=fig.transFigure))
 txt(x+5,352,label,fontsize=6.2,va='center')
txt(379,365,'G–I: same ten regions and order.',fontsize=5.8,va='top')
txt(379,375,'Cost benchmark: 2 USD/kg.',fontsize=5.8,va='top')
fig.canvas.draw()
for artist in updated_label_artists:
 bbox=artist.get_window_extent(fig.canvas.get_renderer())
 updated_label_rects.append(fitz.Rect(bbox.x0*72/fig.dpi,H-bbox.y1*72/fig.dpi,bbox.x1*72/fig.dpi,H-bbox.y0*72/fig.dpi))
require_matplotlib_panel_alignment(fig,axes=axes,panel_ids=['D','E','F','G','H','I'],row_groups=[],column_groups=[['D','E','F'],['G','H','I']],require_panel_labels=False,tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True,json_out=ROOT/'panel_alignment.json')
fig.savefig(ROOT/'DEF_GHI_editable.pdf',transparent=True);fig.savefig(ROOT/'DEF_GHI_editable.svg',transparent=True);plt.close(fig)
# Keep the approved A-C map and color-bar geometry; replace display labels only.
final=fitz.open(); page=final.new_page(width=W,height=H)
# Remove only old D-F latitude labels crossing the column seam from an assembly copy.
left=fitz.open(OLD/'Original_Figure_2.pdf')
for shift in [0,114.21,228.42]:
 left[0].add_redact_annot(fitz.Rect(185,11+shift,200,86+shift),fill=None,cross_out=False)
left[0].add_redact_annot(fitz.Rect(191,0,W,H),fill=None,cross_out=False)
left[0].apply_redactions(images=0,graphics=1,text=0)
for rect in updated_label_rects[:7]:
 left[0].add_redact_annot(rect,fill=None,cross_out=False)
left[0].apply_redactions(images=0,graphics=0,text=0)
clip=fitz.Rect(0,0,191,H);page.show_pdf_page(clip,left,0,clip=clip,keep_proportion=False)
new=fitz.open(ROOT/'DEF_GHI_editable.pdf');rect=fitz.Rect(191,0,W,H);page.show_pdf_page(rect,new,0,clip=rect,keep_proportion=False)
page.show_pdf_page(clip,new,0,clip=clip,keep_proportion=False)
final.set_metadata({'title':'Figure 3. Hydrogen production costs under annual-average and hourly assessments'})
base=ROOT/'Figure_2_Fixed_Benchmark_Cost_Pairs';final.save(str(base)+'.pdf',garbage=4,deflate=True);final.close();new.close()
doc=fitz.open(str(base)+'.pdf');doc[0].get_pixmap(dpi=300,alpha=False).save(str(base)+'.png')
base.with_suffix('.svg').write_text(doc[0].get_svg_image(text_as_path=False),encoding='utf-8')
doc.close(); original.close(); left.close(); fitz.TOOLS.store_shrink(100)
original=fitz.open(OLD/'Original_Figure_2.pdf'); doc=fitz.open(str(base)+'.pdf')
regions=[fitz.Rect(0,0,184.5,H)]+[fitz.Rect(184.5,96+j*114.21,191,107+j*114.21) for j in range(3)]
for clipcheck in regions:
 before=original[0].get_pixmap(matrix=fitz.Matrix(3,3),clip=clipcheck,alpha=False)
 after=doc[0].get_pixmap(matrix=fitz.Matrix(3,3),clip=clipcheck,alpha=False)
 a=np.frombuffer(before.samples,dtype=np.uint8).reshape(before.height,before.width,3)
 b=np.frombuffer(after.samples,dtype=np.uint8).reshape(after.height,after.width,3)
 assert a.shape==b.shape
 mask=np.ones(a.shape[:2],dtype=bool)
 for rect in updated_label_rects:
  bounds=fitz.Rect(rect.x0-1,rect.y0-1,rect.x1+1,rect.y1+1)&clipcheck
  if bounds.is_empty: continue
  x0=max(0,int(np.floor(bounds.x0*3-before.x))); x1=min(before.width,int(np.ceil(bounds.x1*3-before.x)))
  y0=max(0,int(np.floor(bounds.y0*3-before.y))); y1=min(before.height,int(np.ceil(bounds.y1*3-before.y)))
  mask[y0:y1,x0:x1]=False
 assert np.array_equal(a[mask],b[mask]),'A-C artwork outside updated labels changed'
qa={'year_specific_thresholds':TARGETS,'A_C_artwork_pixel_identical_outside_updated_labels':True,'A_C_updated_display_labels':7,'matched_nodes':d.groupby('year').size().to_dict(),'unknown_counts':d[d.region_name=='Unknown'].groupby('year').size().to_dict(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'threshold_rule':'static <= t and hourly > t defines static-only success','regional_selection':'same 10 regions and order selected by lowest 2035 hourly regional medians; Unknown retained globally','uncertainty':'descriptive census of matched model locations; no confidence intervals','reverse_counts':glob[['year','target_usd_kg','cat3_n']].to_dict('records')}
(ROOT/'data_checks.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
shutil.copy2(SOURCE,ROOT/'source_data'/SOURCE.name)
print(glob.to_string(index=False));print('A-C artwork outside updated labels is pixel identical; outputs saved.')
