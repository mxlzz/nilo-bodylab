import argparse
import hashlib
import importlib.util
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path

E1 = Path(__file__).resolve().parent.parent / "E1-01" / "run.py"
E1_HASH = "2777c4765618eb68d404657bf8fa4d3f7060adebdd59b8039ca66c9d4d509932"
assert hashlib.sha256(E1.read_bytes()).hexdigest() == E1_HASH
spec = importlib.util.spec_from_file_location("e1_frozen", E1)
e1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e1)


def exact(T, Ta, C, G, power, duration):
    if G == 0:
        return T + power*duration/C
    equilibrium = Ta + power/G
    return equilibrium + (T-equilibrium)*math.exp(-G*duration/C)


def run_case(case, dt, cfg, model, snapshot=None, start=0):
    q, eta = cfg["q_J_per_kg"], cfg["work_efficiency"]
    C, G = case["C_J_K"], case["G_W_K"]
    mass = case["ready"]+case["pending"]+case["external"]
    structure = cfg["structure_kg"]
    scale = max(1.0, q*mass, C*20)
    H0 = C*case["T_K"] if model=="T1" else 0.0
    s, H, B = (e1.initial(case,case["metabolic"]),H0,0.0) if snapshot is None else (
        dict(snapshot["s"]),snapshot["H"],snapshot["B"])
    T = H/C if model=="T1" else None
    ref, refB = case["T_K"], 0.0
    max_m = max_e = max_f = 0.0
    minimum = min(s[k] for k in ("X","P","R","W"))
    minT = T
    heat_in = heat_out = 0.0
    ends = []
    begin = time.perf_counter()
    steps = 0
    for seg in case["segments"][start:]:
        Ta = seg["ambient_K"]
        duration = seg["duration"]
        expected = q*(seg["maintenance"]+seg["activity"]*(1-eta))
        n = round(duration/dt)
        assert n*dt == duration
        old_ref = ref
        for _ in range(n):
            oldQ = s["Q"]
            e1.step(s,seg,case["metabolic"],case["k"],dt,q,eta)
            g = s["Q"]-oldQ
            if case["metabolic"]=="A0":
                max_f=max(max_f,abs(g-expected*dt))
            if model=="T1":
                b=G*(T-Ta)*dt
                H+=g-b
                B+=b
                T=H/C
                minT=min(minT,T)
                heat_in+=max(0.0,-b)
                heat_out+=max(0.0,b)
            else:
                B+=g
                T=Ta+g/(G*dt) if G else None
            if case["metabolic"]=="A1":
                ref=exact(ref,Ta,C,G,g/dt,dt)
                refB+=g
            max_m=max(max_m,abs(s["X"]+s["P"]+s["R"]+s["W"]+structure-(mass+structure))/max(1.0,mass))
            max_e=max(max_e,abs(q*(s["X"]+s["P"]+s["R"])+s["L"]+H+B-q*mass-H0)/scale)
            minimum=min(minimum,*(s[k] for k in ("X","P","R","W")))
            steps+=1
        if case["metabolic"]=="A0":
            ref=exact(ref,Ta,C,G,expected,duration)
            refB+=expected*duration
        ends.append(dict(T=T,H=H,B=B,s=dict(s),ref_T=ref,
                         ref_B=refB-C*(ref-case["T_K"])))
    err=max(abs(x["T"]-x["ref_T"]) for x in ends) if model=="T1" else None
    common=max(abs(x["T"]-x["ref_T"]) for x in ends) if model=="T0" and G else None
    return dict(ends=ends,err=err,common=common,mass=max_m,energy=max_e,
                forcing=max_f,minimum=minimum,minT=minT,heat_in=heat_in,heat_out=heat_out,
                steps=steps,seconds=time.perf_counter()-begin)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    begin=time.perf_counter()
    data=Path(args.config).read_bytes()
    cfg=json.loads(data)
    t=cfg["tolerances"]
    fine=min(cfg["dt_s"])
    records=[]
    for case in cfg["cases"]:
        for model in ("T0","T1"):
            for dt in cfg["dt_s"]:
                r=run_case(case,dt,cfg,model)
                replay=None
                if dt==fine and model=="T1":
                    snap=json.loads(json.dumps(r["ends"][0],allow_nan=False))
                    resumed=run_case(case,dt,cfg,model,snap,1)
                    physical=lambda ends:[{k:x[k] for k in ("T","H","B","s")} for x in ends]
                    replay=physical(resumed["ends"])==physical(r["ends"][1:])
                records.append(dict(id=case["id"],set=case["set"],model=model,dt=dt,replay=replay,**r))
    f=[r for r in records if r["dt"]==fine]
    by={(r["id"],r["model"]):r for r in f}
    def r(id,model="T1"):
        return by[(id,model)]
    def Ts(id,model="T1"):
        return [e["T"] for e in r(id,model)["ends"]]
    def last(id,model="T1"):
        return r(id,model)["ends"][-1]
    fine_err=max(x["err"] for x in f if x["model"]=="T1")
    double_err=max(x["err"] for x in records if x["model"]=="T1" and x["dt"]==2*fine)
    balance=max(max(x["mass"],x["energy"]) for x in records)
    elapsed=time.perf_counter()-begin
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    eps=t["control_K"]
    checks=dict(balance=balance<=t["balance"],
        admissible=all(x["minimum"]>=0 and (x["model"]=="T0" or x["minT"]>0) for x in records),
        forcing=all(x["forcing"]<=t["heat_forcing_J"] for x in records),
        reference=fine_err<=t["temperature_K"],
        convergence=fine_err<=t["convergence_ratio"]*double_err or max(fine_err,double_err)<=eps,
        steady=all(abs(T-300)<=eps for m in ("T0","T1") for T in Ts("steady",m)),
        cooling=290<Ts("cooling")[-1]<Ts("cooling")[0]<310 and last("cooling")["B"]>0,
        insulated=abs(last("insulated")["B"])<=eps and
            abs(last("insulated")["T"]-300-last("insulated")["s"]["Q"]/10)<=eps and
            all(v is None for v in Ts("insulated","T0")),
        activity=Ts("activity")[0]>300 and Ts("activity")[-1]<Ts("activity")[0],
        reversal=r("ambient-reversal")["heat_in"]>0 and r("ambient-reversal")["heat_out"]>0,
        pending=last("pending-coupling")["s"]["P"]>0 and last("pending-coupling")["s"]["Q"]>0,
        replay=all(x["replay"] is True for x in f if x["model"]=="T1"),
        resources=elapsed<=t["wall_s"] and rss<=t["rss_MiB"])
    h1=dict(reserved=all(x["err"]<=t["temperature_K"] for x in f if x["model"]=="T1" and x["set"]=="reserved"),
        baseline_fails=any(r(id,"T0")["common"]>t["baseline_failure_K"] for id in ("ambient-reversal","history-hot","history-cold")),
        history=Ts("history-hot","T0")==Ts("history-cold","T0") and
            Ts("history-hot")[0]-Ts("history-cold")[0]>t["baseline_failure_K"])
    h0=all(x["common"] is not None and x["common"]<=t["temperature_K"] for x in f if x["model"]=="T0")
    verdict="H1_conditional" if all(checks.values()) and all(h1.values()) else (
        "H0_sufficient" if all(checks.values()) and h0 else "inconclusive")
    out=dict(protocol="E2-T01",python=sys.version,platform=platform.platform(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(data).hexdigest(),e1_sha256=E1_HASH,
        wall_s=elapsed,rss_MiB=rss,checks=checks,h1_checks=h1,h0=h0,verdict=verdict,
        max_balance_residual=balance,fine_error_K=fine_err,double_dt_error_K=double_err,
        records=records)
    Path(args.out).write_text(json.dumps(out,separators=(",",":"),allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="records"},indent=2))
    return 0 if all(checks.values()) else 1


if __name__=="__main__":
    raise SystemExit(main())
