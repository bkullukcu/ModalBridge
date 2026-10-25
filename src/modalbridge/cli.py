import argparse,json,sys
from .core import match_modes
from .io import load_modes

from . import __version__


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('convert', 'audit-inputs'):
        from .user_data import convert, audit_pair
        p = argparse.ArgumentParser(description='Convert or audit external physical DOF data')
        s = p.add_subparsers(dest='command', required=True)
        c = s.add_parser('convert'); c.add_argument('input'); c.add_argument('--schema', required=True); c.add_argument('--output', default='converted_modes.npz')
        a = s.add_parser('audit-inputs'); a.add_argument('reference'); a.add_argument('candidate'); a.add_argument('--tolerance-m', type=float, default=1e-4)
        args = p.parse_args()
        result = convert(args.input, args.schema, args.output) if args.command == 'convert' else audit_pair(args.reference, args.candidate, args.tolerance_m)
        print(json.dumps(result, indent=2))
        return
    p=argparse.ArgumentParser(description='Match two NPZ mode/response sets on explicit common physical DOFs',
        epilog='Import your own data first with: modalbridge convert INPUT --schema SCHEMA.json --output OUT.npz | modalbridge audit-inputs REF.npz CAND.npz (see docs/USER_DATA_IMPORT.md).')
    p.add_argument('--version', action='version', version='%(prog)s '+__version__)
    p.add_argument('reference');p.add_argument('candidate');p.add_argument('--min-mac',type=float,default=.6);p.add_argument('--max-shift',type=float,default=.2);p.add_argument('--output',default='matches.json');a=p.parse_args()
    import numpy as np
    with np.load(a.reference, allow_pickle=False) as za, np.load(a.candidate, allow_pickle=False) as zb:
        if 'reference_frame' in za.files or 'reference_frame' in zb.files:
            if 'reference_frame' not in za.files or 'reference_frame' not in zb.files:
                raise ValueError('both datasets must be imported/audited when physical metadata exists')
            from .user_data import audit_pair
            audit_pair(a.reference, a.candidate)
    r=match_modes(load_modes(a.reference),load_modes(a.candidate),min_mac=a.min_mac,max_relative_shift=a.max_shift)
    with open(a.output,'w') as f:json.dump({'pairs':r['pairs'],'common_dofs':r['common_dofs'],'mac':r['mac'].tolist()},f,indent=2)
    print(a.output)
if __name__=='__main__':main()
