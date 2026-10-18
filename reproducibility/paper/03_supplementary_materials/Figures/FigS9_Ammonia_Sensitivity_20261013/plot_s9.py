from pathlib import Path
from io import BytesIO
import json, sys
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
sys.path.insert(0,str(Path(__file__).parent))
from audit_panel_alignment import require_matplotlib_panel_alignment
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'source_data'
OUT=ROOT
QA=ROOT/'qa'; QA.mkdir(exist_ok=True)
r=pd.read_csv(DATA/'scenario_results.csv')
c=pd.read_csv(DATA/'storage_responses.csv')
k=pd.read_csv(DATA/'cost_changes.csv')
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.2,'axes.labelsize':7.2,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7.2,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.linewidth':.5,'axes.spines.top':False,'axes.spines.right':False,'xtick.major.size':2,'ytick.major.size':0,'xtick.major.width':.5,'ytick.major.width':.5,'text.color':'#263238','axes.labelcolor':'#263238','xtick.color':'#263238','ytick.color':'#263238','legend.frameon':False,'savefig.facecolor':'white'})
BLUE='#286879'; ORANGE='#CF8A30'; PURPLE='#826B98'; GRAY='#89969B'; PALE='#DCE2E4'; INK='#263238'
W,H=528,620
X=[98,243,388]; WIDTH=124
profiles=['HighPEM','HighBat','LowBat','HighFlex','LowFlex']
labels=['PEM CAPEX +30%','Battery power CAPEX ×2','Battery power CAPEX ×0.5','Relaxed operation','Tighter operation']
component_colors={'Electrolyzers':BLUE,'Battery':GRAY,'H2 storage':PURPLE,'Other system':'#DDD3C4'}
cmap=LinearSegmentedColormap.from_list('capacity_change',[BLUE,'#FAFAF8',ORANGE])
norm=Normalize(-250,250)
products=[('ammonia','Green ammonia','S9')]
exports=[]
for product,name,number in products:
    fig=plt.figure(figsize=(W/72,H/72))
    axes=[]
    def text(x,y,s,size=7.2,ha='left',weight='normal',color=INK):
        return fig.text(x/W,y/H,s,fontsize=size,ha=ha,va='center',weight=weight,color=color)
    def ax(x,y,h,label):
        a=fig.add_axes([x/W,y/H,WIDTH/W,h/H],label=label)
        axes.append(a)
        return a
    def legend(handles,labels,x,y,ncol):
        fig.legend(handles,labels,loc='center left',bbox_to_anchor=(x/W,y/H),ncol=ncol,frameon=False,borderaxespad=0,handlelength=1.2,handletextpad=.45,columnspacing=1.15)
    text(98,579,'Electrolyzer configuration',8.5,weight='bold')
    legend([Patch(facecolor=BLUE),Patch(facecolor=ORANGE)],['AE','PEM'],360,579,2)
    text(98,371,'Storage capacity response',8.5,weight='bold')
    text(98,165,'Cost consequences',8.5,weight='bold')
    legend([Patch(facecolor=v) for v in component_colors.values()],list(component_colors),195,165,4)
    for j,(site,site_name) in enumerate([('W','Wind-cluster'),('H','Wind–solar complementary'),('S','Solar-cluster')]):
        x=X[j]
        text(x+WIDTH/2,603,site_name,10.3,ha='center',weight='bold')
        part=r[(r['product']==product)&(r.site==site)].set_index('profile')
        a=ax(x,422,125,chr(65+j))
        p=['Base']+profiles
        y=np.arange(6)
        a.barh(y,part.loc[p,'AE_pct_base_total'],height=.60,color=BLUE,zorder=3)
        a.barh(y,part.loc[p,'PEM_pct_base_total'],left=part.loc[p,'AE_pct_base_total'],height=.60,color=ORANGE,zorder=3)
        
        for gap in np.arange(-.5,6,1):
            a.plot([100,100],[gap-.18,gap+.18],color='#B5BFC2',lw=.65,zorder=1)
        a.axhline(3.5,color=PALE,lw=.6,zorder=0)
        a.set_xlim(0,130); a.set_xticks([0,50,100])
        a.set_ylim(5.65,-.65)
        a.set_yticks(y,labels=['Base']+labels if j==0 else ['']*6)
        a.spines['left'].set_visible(False)
        a.set_xlabel('Electrolyzer capacity (% of baseline)',labelpad=3)
        text(x,560,chr(65+j),9,weight='bold')
        for iy,profile in enumerate(p):
            ae,pe=part.loc[profile,['AE_pct_base_total','PEM_pct_base_total']]
            if ae>=23:
                a.text(ae/2,iy,f'{ae:.1f}',color='white',ha='center',va='center',fontsize=7.2)
            if pe>=23:
                a.text(ae+pe/2,iy,f'{pe:.1f}',color=INK,ha='center',va='center',fontsize=7.2)
        b=ax(x,242,100,chr(68+j))
        cp=c[(c['product']==product)&(c.site==site)&(c.profile!='Base')]
        matrix=cp.pivot(index='profile',columns='metric',values='change_pct').loc[profiles,['Battery power','Battery energy','H2 storage']].to_numpy()
        assert np.isfinite(matrix).all() and np.abs(matrix).max()<=250
        im=b.imshow(matrix,cmap=cmap,norm=norm,aspect='auto',interpolation='nearest',extent=[-.5,2.5,4.5,-.5])
        b.set_yticks(range(5),labels=labels if j==0 else ['']*5)
        b.set_xticks(range(3),labels=['Battery\npower','Battery\nenergy','H2\nstorage'])
        b.tick_params(axis='x',length=0,pad=5)
        for spine in b.spines.values(): spine.set_visible(False)
        for row in range(5):
            for col in range(3):
                val=matrix[row,col]
                s='0.0' if abs(val)<.05 else f'{val:+.1f}'
                b.text(col,row,s,ha='center',va='center',fontsize=7.4,color='white' if val<-160 else INK)
        b.set_xticks(np.arange(-.5,3,1),minor=True)
        b.set_yticks(np.arange(-.5,5,1),minor=True)
        b.grid(which='minor',color='white',lw=1.2); b.tick_params(which='minor',length=0)
        text(x,355,chr(68+j),9,weight='bold')
        d=ax(x,31,100,chr(71+j))
        kp=k[(k['product']==product)&(k.profile!='Base')]
        sums=kp.groupby(['site','profile']).change_USD_t.agg(positive=lambda z:z.clip(lower=0).sum(),negative=lambda z:z.clip(upper=0).sum())
        lo=float(sums.negative.min()); hi=float(sums.positive.max())
        span=hi-lo
        xmin=lo-.06*span; xmax=hi+.48*span
        for yi,profile in enumerate(profiles):
            vals=kp[(kp.site==site)&(kp.profile==profile)].set_index('component')
            pos=neg=0.
            for component,color in component_colors.items():
                value=float(vals.loc[component,'change_USD_t'])
                d.barh(yi,value,left=pos if value>=0 else neg,height=.46,color=color,zorder=2)
                if value>=0: pos+=value
                else: neg+=value
            net=float(part.loc[profile,'LCOP_change_USD_t'])
            d.plot(net,yi,marker='D',ms=3.4,mfc='white',mec=INK,mew=.7,zorder=5)
            d.text(.98,yi,f'{part.loc[profile,"LCOP_change_pct"]:+.1f}%',transform=d.get_yaxis_transform(),ha='right',va='center',fontsize=7,color=INK)
        d.axvline(0,color='#B5BFC2',lw=.6,zorder=1)
        d.axhline(2.5,color=PALE,lw=.6,zorder=0)
        d.set_xlim(xmin,xmax); d.set_ylim(4.6,-.6)
        d.set_yticks(range(5),labels=labels if j==0 else ['']*5)
        d.spines['left'].set_visible(False)
        d.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=3))
        d.set_xlabel('Cost change (USD/t)',labelpad=3)
        text(x,145,chr(71+j),9,weight='bold')
        text(x+WIDTH,145,'Total cost change (%)',6.8,ha='right')
    cax=fig.add_axes([206/W,202/H,198/W,6/H],label='colorbar')
    cb=fig.colorbar(im,cax=cax,orientation='horizontal',ticks=[-250,-125,0,125,250])
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6.5,length=2,pad=2)
    text(98,205,'Change from baseline (%)',7)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,axes=axes,panel_ids=[a.get_label() for a in axes],row_groups=[list('ABC'),list('DEF'),list('GHI')],column_groups=[list('ADG'),list('BEH'),list('CFI')],exemptions=[{'panels':[a.get_label() for a in axes],'checks':['vertical-gutter'],'reason':'Different row functions reserve different space for shared legends and colorbar; all columns repeat exactly the same row positions.'}],json_out=QA/f'{number}_alignment.json',strict=True)
    stem=OUT/f'Figure_{number}_Flexibility_Reallocation'
    fig.savefig(stem.with_suffix('.pdf'))
    fig.savefig(stem.with_suffix('.svg'))
    fig.savefig(stem.with_suffix('.png'),dpi=300)
    raster=BytesIO()
    fig.savefig(raster,format='tiff',dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    stem.with_suffix('.tiff').write_bytes(raster.getvalue())
    plt.close(fig)
    caption=('Equipment and storage responses to costs and operating constraints in green-ammonia production. '
    'Columns show wind-cluster, wind–solar complementary and solar-cluster sites under 2035 technology assumptions. '
    '(A-C) AE and PEM capacities expressed as percentages of the corresponding baseline total electrolyzer capacity; the dashed line marks 100%. '
    '(D-F) Percentage changes in battery power, battery energy and hydrogen-storage capacity, using a shared color scale. '
    '(G-I) Changes in component contributions to production cost. Positive and negative contributions are stacked separately; white diamonds show the net cost change, and right-hand labels show the total percentage change. '
    'Other system includes renewable generation, synthesis and remaining modeled costs. '
    'Changes are relative to the baseline at each site. '
    'PEM CAPEX increases by 30%; battery power CAPEX doubles or halves. '
    'Relaxed and tighter operation vary synthesis minimum-load and ramping limits (Supplementary Table S2).')
    (OUT/f'Figure_{number}_Legend.txt').write_text(caption,encoding='utf-8')
    exports.append(dict(product=product,figure=number,width_mm=W/72*25.4,height_mm=H/72*25.4,pdf=str(stem.with_suffix('.pdf'))))
(ROOT/'export_manifest.json').write_text(json.dumps(exports,indent=2),encoding='utf-8')
print(json.dumps(exports,indent=2))



