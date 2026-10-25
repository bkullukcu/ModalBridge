"""Known-truth mode permutation, phase invariance and rejection demonstration."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from modalbridge import *

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='examples/output');a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 rng=np.random.default_rng(2026);q=np.linalg.qr(rng.normal(size=(30,6)))[0];ids=tuple(map(str,range(30)))
 ref=ModeSet([40,65,90,115],q[:,:4],ids);candidate=ModeSet([66,41,116,145],q[:,[1,0,3,5]]*np.exp(1j*np.array([.2,2.,1.,.5])),ids)
 r=match_modes(ref,candidate);st=assignment_stability(ref,candidate,n_boot=300)
 fig,ax=plt.subplots(1,2,figsize=(7.2,3.1),layout='constrained');im=ax[0].imshow(r['mac'],vmin=0,vmax=1,cmap='viridis');fig.colorbar(im,ax=ax[0],label='Complex MAC');ax[0].set(xlabel='Candidate index',ylabel='Reference index',title='A  Known correspondence')
 im=ax[1].imshow(st['frequency'],vmin=0,vmax=1,cmap='Blues');fig.colorbar(im,ax=ax[1],label='Resampling frequency');ax[1].set(xticks=range(5),xticklabels=['0','1','2','3','None'],xlabel='Assigned candidate',ylabel='Reference index',title='B  Rejection of missing mode')
 fig.suptitle('SYNTHETIC VERIFICATION - known permutation and missing mode',fontsize=10)
 for ext in ['pdf','svg','png']:fig.savefig(out/('synthetic_matching.'+ext),dpi=400,bbox_inches='tight')
 for name,s in [('reference',ref),('candidate',candidate)]:np.savez_compressed(out/(name+'.npz'),frequency=s.frequency,shapes=s.shapes,dof_ids=np.array(s.dof_ids))
 (out/'synthetic_results.json').write_text(json.dumps({'pairs':r['pairs'],'known_truth':[1,0,None,2]},indent=2));plt.close(fig)
if __name__=='__main__':main()
