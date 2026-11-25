import argparse
import hashlib
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path


def initial(case, model):
    p, r = case["pending"], case["ready"]
    return dict(X=case["external"], P=p if model == "A1" else 0.0,
                R=r if model == "A1" else r+p, W=0.0, Q=0.0, L=0.0,
                unmet=0.0, time=0.0, served_fraction=1.0)


def pulse(s, seg, model):
    u = min(seg["pulse"], s["X"])
    s["X"] -= u
    s["P" if model == "A1" else "R"] += u
    return u


def step(s, seg, model, k, dt, q, eta):
    a = min(s["P"], k*s["P"]*dt) if model == "A1" else 0.0
    s["P"] -= a
    s["R"] += a
    d = seg["maintenance"]+seg["activity"]
    want = d*dt
    c = min(s["R"], want)
    cm = c*(seg["maintenance"]/d) if d else 0.0
    cb = c-cm
    work = q*eta*cb
    s["R"] -= c
    s["W"] += c
    s["L"] += work
    s["Q"] += q*c-work
    s["unmet"] += want-c
    s["time"] += dt
    s["served_fraction"] = c/want if want else 1.0
    assert 0 <= c <= want and 0 <= a and 0 <= cm <= c
    return dict(transfer=a, consumed=c, maintenance=cm, activity=cb,
                requested=want, rejected=want-c)


def simulate(case, model, dt, cfg, checkpoint=None, start=0):
    q, eta = cfg["q_J_per_kg"], cfg["work_efficiency"]
    mass = case["external"]+case["pending"]+case["ready"]
    scale = max(1.0, mass)
    structure = cfg["structure_kg"]
    s = initial(case, model) if checkpoint is None else dict(checkpoint)
    ends, pulses = [], []
    max_mass = max_energy = 0.0
    minimum = min(s[x] for x in ("X","P","R","W","Q","L"))
    steps = 0
    begin = time.perf_counter()
    def inspect():
        nonlocal max_mass, max_energy, minimum
        max_mass = max(max_mass, abs(s["X"]+s["P"]+s["R"]+s["W"]+structure-(mass+structure))/scale)
        max_energy = max(max_energy, abs(q*(s["X"]+s["P"]+s["R"])+s["Q"]+s["L"]-q*mass)/(q*scale))
        minimum = min(minimum, *(s[x] for x in ("X","P","R","W","Q","L","unmet")))
    inspect()
    for seg in case["segments"][start:]:
        u = pulse(s, seg, model)
        pulses.append(dict(requested=seg["pulse"], actual=u, rejected=seg["pulse"]-u))
        inspect()
        n = round(seg["duration"]/dt)
        assert n*dt == seg["duration"]
        for _ in range(n):
            step(s, seg, model, case["k"], dt, q, eta)
            inspect()
            steps += 1
        ends.append(dict(s))
    return dict(ends=ends, pulses=pulses, max_mass_residual=max_mass,
                max_energy_residual=max_energy, minimum_state=minimum, steps=steps,
                seconds=time.perf_counter()-begin)


def reference(case, model, cfg):
    # Closed-form integration by segment; no call to step/pulse/initial.
    q, eta = cfg["q_J_per_kg"], cfg["work_efficiency"]
    x = case["external"]
    p = case["pending"] if model == "A1" else 0.0
    r = case["ready"] + (case["pending"] if model == "A0" else 0.0)
    w = heat = work = unmet = t = 0.0
    ends = []
    for z in case["segments"]:
        accepted = min(x, z["pulse"])
        x -= accepted
        if model == "A1":
            p += accepted
        else:
            r += accepted
        duration = z["duration"]
        remaining = p*math.exp(-case["k"]*duration)
        supply = r+p-remaining
        d = z["maintenance"]+z["activity"]
        used = min(d*duration, supply)
        mechanical = q*eta*used*(z["activity"]/d) if d else 0.0
        p, r = remaining, supply-used
        w += used
        work += mechanical
        heat += q*used-mechanical
        unmet += d*duration-used
        t += duration
        ends.append(dict(X=x,P=p,R=r,W=w,Q=heat,L=work,unmet=unmet,time=t))
    return ends


def error(ends, target, fields, scale, q):
    return max(abs(a[k]-b[k])/(scale*(q if k in ("Q","L") else 1.0))
               for a,b in zip(ends,target,strict=True) for k in fields)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    data = Path(args.config).read_bytes()
    cfg = json.loads(data)
    tol = cfg["tolerances"]
    q = cfg["q_J_per_kg"]
    results = []
    fine = min(cfg["dt_s"])
    for case in cfg["cases"]:
        scale = max(1.0,case["external"]+case["pending"]+case["ready"])
        refs = {m:reference(case,m,cfg) for m in ("A0","A1")}
        for model in ("A0","A1"):
            for dt in cfg["dt_s"]:
                run = simulate(case,model,dt,cfg)
                own = error(run["ends"],refs[model],("W","P","R","Q","L"),scale,q)
                common = error(run["ends"],refs["A1"],("W","L"),scale,q)
                replay = None
                if dt == fine:
                    snap = json.loads(json.dumps(run["ends"][0],allow_nan=False))
                    resumed = simulate(case,model,dt,cfg,snap,1)
                    replay = resumed["ends"] == run["ends"][1:]
                results.append(dict(case=case["id"],set=case["set"],model=model,dt=dt,
                                    own_error=own,common_error=common,replay=replay,
                                    reference=refs[model],**run))
    f = [r for r in results if r["dt"] == fine]
    by = {(r["case"],r["model"]):r for r in f}
    def pair(case_a,model_a,case_b,model_b):
        a,b=by[(case_a,model_a)],by[(case_b,model_b)]
        return max(abs(x[k]-y[k])/(q if k in ("Q","L") else 1)
                   for x,y in zip(a["ends"],b["ends"],strict=True) for k in ("W","Q","L"))
    fine_err=max(r["own_error"] for r in f if r["model"]=="A1")
    coarse_err=max(r["own_error"] for r in results if r["model"]=="A1" and r["dt"]==2*fine)
    balance=max(max(r["max_mass_residual"],r["max_energy_residual"]) for r in results)
    checks=dict(balance=balance<=tol["balance_relative"],
                nonnegative=all(r["minimum_state"]>=0 for r in results),
                own_reference=all(r["own_error"]<=tol["reference_relative"] for r in f),
                convergence=fine_err<=tol["convergence_ratio"]*coarse_err or
                    max(fine_err,coarse_err)<=tol["balance_relative"],
                replay=all(r["replay"] is True for r in f),
                ready_control=pair("ready-control","A0","ready-control","A1")<=tol["balance_relative"],
                empty_control=pair("empty-control","A0","empty-control","A1")<=tol["balance_relative"],
                no_demand=all(s[k]==0 for m in ("A0","A1") for s in by[("no-demand",m)]["ends"] for k in ("W","Q","L")),
                finite_pulse=all(p["actual"]<=p["requested"] and p["actual"]>=0 and p["rejected"]>=0 for r in results for p in r["pulses"])
                    and all(by[("empty-control",m)]["pulses"][0]["actual"]==0 and
                            abs(by[("recovery",m)]["pulses"][-1]["actual"]-0.4)<=tol["balance_relative"] for m in ("A0","A1")))
    h1=dict(A1_reserved=all(r["common_error"]<=tol["reference_relative"] for r in f if r["model"]=="A1" and r["set"]=="reserved"),
            A0_pending_fails=by[("paired-pending","A0")]["common_error"]>tol["baseline_failure_relative"],
            A0_pair_identical=pair("paired-ready","A0","paired-pending","A0")==0,
            A0_ready=by[("paired-ready","A0")]["common_error"]<=tol["reference_relative"])
    h0=all(r["common_error"]<=tol["reference_relative"] for r in f if r["model"]=="A0")
    elapsed=time.perf_counter()-start
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    checks["resources"]=elapsed<=tol["max_wall_s"] and rss<=tol["max_rss_mib"]
    verdict="H1_conditional" if all(checks.values()) and all(h1.values()) else (
        "H0_sufficient" if all(checks.values()) and h0 else "inconclusive")
    out=dict(protocol="E1-01",python=sys.version,platform=platform.platform(),
             config_sha256=hashlib.sha256(data).hexdigest(),
             source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             wall_s=elapsed,rss_mib=rss,checks=checks,h1_checks=h1,h0=h0,verdict=verdict,
             max_balance_residual=balance,fine_error=fine_err,coarse_error=coarse_err,
             runs=results)
    Path(args.out).write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="runs"},indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
