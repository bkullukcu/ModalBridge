"""Generate auditable README figures from synthetic complex response shapes.

    python examples/make_readme_figures.py

The example contains one deliberately unmatched response. It is not a damage
identification result or a comparison of experimental eigenmodes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from modalbridge import ModeSet, match_modes

BLUE='#245778'; ORANGE='#ce7950'; TEAL='#0d8278'; DARK='#23313f'; MUTED='#61707b'


def configure(latex):
    plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':10,
        'axes.titlesize':12,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,
        'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#66727b',
        'axes.labelcolor':DARK,'text.color':DARK,'xtick.color':MUTED,'ytick.color':MUTED,
        'svg.fonttype':'path','text.usetex':latex,'figure.facecolor':'white','axes.facecolor':'white'})


def demo_modes():
    rng=np.random.default_rng(13)
    q,_=np.linalg.qr(rng.normal(size=(14,5))+1j*rng.normal(size=(14,5)))
    reference=q[:,:4]
    # Deliberately remove reference #3 and add an orthogonal, new candidate.
    cand=np.column_stack([reference[:,1],reference[:,0],reference[:,3],q[:,4]])
    cand=cand + .018*(rng.normal(size=cand.shape)+1j*rng.normal(size=cand.shape))
    ids=tuple(f'p{i:02d}_z' for i in range(len(q)))
    a=ModeSet([42.,73.,116.,155.],reference,ids,label='Reference')
    b=ModeSet([74.2,42.8,157.5,210.0],cand*np.exp(.65j),ids,label='Changed configuration')
    return a,b,match_modes(a,b,min_mac=.6,max_relative_shift=.2)


def render(out):
    a,b,res=demo_modes()
    mac=res['mac']
    fig,ax=plt.subplots(figsize=(7.5,4.7))
    im=ax.imshow(mac,cmap='viridis',vmin=0,vmax=1,aspect='equal')
    ax.set_xticks(range(len(b.frequency)),[f'C{i+1} ({f:.1f} Hz)' for i,f in enumerate(b.frequency)],rotation=25,ha='right')
    ax.set_yticks(range(len(a.frequency)),[f'R{i+1} ({f:.0f} Hz)' for i,f in enumerate(a.frequency)])
    ax.set(xlabel='Candidate response',ylabel='Reference response',title='Complex MAC on shared physical DOFs')
    for i in range(mac.shape[0]):
        for j in range(mac.shape[1]):
            ax.text(j,i,f'{mac[i,j]:.2f}',color='white' if mac[i,j]<.50 else '#142733',ha='center',va='center',fontsize=9)
    for p in res['pairs']:
        if p['candidate'] is not None:
            ax.add_patch(Rectangle((p['candidate']-.48,p['reference']-.48),.96,.96,fill=False,ec=ORANGE,lw=2.2))
    cb=fig.colorbar(im,ax=ax,shrink=.80,pad=.035)
    cb.set_label('Complex MAC')
    fig.subplots_adjust(left=.17,right=.87,top=.85,bottom=.25)
    fig.text(.87,.06,'Orange boxes: accepted correspondences  |  synthetic vectors',ha='right',fontsize=8,color=MUTED)
    fig.savefig(out/'complex_mac.svg',format='svg',metadata={'Date':None,'Creator':'ModalBridge deterministic example'})
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.0,4.8))
    for i,f in enumerate(a.frequency):
        ax.scatter(0,f,s=85,color=BLUE,zorder=4)
        ax.annotate(f'R{i+1}',(-.04,f),ha='right',va='center',fontsize=9,color=DARK)
    for j,f in enumerate(b.frequency):
        ax.scatter(1,f,s=85,color=ORANGE,zorder=4)
        ax.annotate(f'C{j+1}',(1.04,f),ha='left',va='center',fontsize=9,color=DARK)
    for p in res['pairs']:
        i=p['reference']; j=p['candidate']
        if j is None:
            ax.scatter(0,a.frequency[i],s=230,facecolors='none',edgecolor=ORANGE,marker='o',lw=1.75,zorder=5)
            ax.text(.48,a.frequency[i]+4.8,'unmatched',ha='center',fontsize=9,color=ORANGE)
        else:
            ax.plot([0,1],[a.frequency[i],b.frequency[j]],color=TEAL,lw=2.15,zorder=2)
            shift=100*(b.frequency[j]-a.frequency[i])/a.frequency[i]
            ax.annotate(f'{shift:+.1f}' + (r'\%' if plt.rcParams['text.usetex'] else '%'),(.49,(a.frequency[i]+b.frequency[j])/2),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9,color=DARK)
    ax.set(xlim=(-.35,1.37),ylim=(25,229),ylabel='Associated frequency (Hz)',title='Frequency-constrained correspondence and abstention')
    ax.set_xticks([0,1],['Reference','Candidate'])
    ax.grid(axis='y',color='#e1e6eb',lw=.7)
    ax.spines['bottom'].set_visible(False)
    fig.subplots_adjust(left=.16,right=.91,top=.84,bottom=.18)
    fig.text(.91,.055,'Synthetic complex response vectors; matching does not establish eigenmode identity',ha='right',fontsize=8,color=MUTED)
    fig.savefig(out/'correspondence.svg',format='svg',metadata={'Date':None,'Creator':'ModalBridge deterministic example'})
    plt.close(fig)
    statuses=[p['status'] for p in res['pairs']]
    assert statuses.count('unmatched')==1, statuses
    print('Wrote two SVG figures; matched=3, unmatched=1 (synthetic)')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'docs'/'figures')
    p.add_argument('--latex',action='store_true',help='Use an installed LaTeX distribution for text')
    args=p.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    configure(args.latex);render(args.output_dir)

if __name__=='__main__':main()
