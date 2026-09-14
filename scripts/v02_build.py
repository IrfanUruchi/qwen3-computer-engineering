#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, os
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))

PURPOSES = {
    "debugging":"v02gen.debugging",
    "code-repair":"v02gen.code_repair",
    "failure-analysis":"v02gen.failure_analysis",
    "design":"v02gen.design",
    "implementation":"v02gen.implementation",
    "testing":"v02gen.testing",
    "troubleshooting":"v02gen.troubleshooting",
    "technical-decision":"v02gen.technical_decision",
}

def status():
    from v02gen.common import scan_v02, DOMAIN_TARGETS, DIFFICULTY_TARGETS
    rows=scan_v02()
    dc=Counter(r["domain"] for r in rows)
    tc=Counter(r["task_type"] for r in rows)
    qc=Counter(r["difficulty"] for r in rows)
    print("v0.2 records:",len(rows))
    print("\nDomains:")
    for d,t in DOMAIN_TARGETS.items():
        print(f"  {d:30s} {dc[d]:3d}/{t:3d}")
    print("\nTask types:")
    for k,v in sorted(tc.items()):
        print(f"  {k:30s} {v:3d}")
    print("\nDifficulty:")
    for d,t in DIFFICULTY_TARGETS.items():
        print(f"  {d:30s} {qc[d]:3d}/{t:3d}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--status",action="store_true")
    ap.add_argument("--purpose",choices=sorted(PURPOSES))
    ap.add_argument("--records",type=int,default=None)
    ap.add_argument("--seed",type=int,default=20260914)
    args=ap.parse_args()

    if args.status or not args.purpose:
        status()
        if not args.purpose:
            return

    defaults = {
        "debugging":10,
        "code-repair":10,
        "failure-analysis":10,
        "design":10,
        "implementation":4,
        "testing":3,
        "troubleshooting":3,
        "technical-decision":3,
    }
    records = args.records if args.records is not None else defaults[args.purpose]

    module=PURPOSES[args.purpose]
    cmd=[sys.executable,"-m",module,"--records",str(records),"--seed",str(args.seed)]

    env=os.environ.copy()
    scripts_dir=str(ROOT/"scripts")
    old_pythonpath=env.get("PYTHONPATH","")
    env["PYTHONPATH"]=scripts_dir if not old_pythonpath else scripts_dir+os.pathsep+old_pythonpath

    raise SystemExit(subprocess.call(cmd,cwd=ROOT,env=env))

if __name__=="__main__":
    main()
