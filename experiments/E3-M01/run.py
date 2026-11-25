import json, math, platform, resource, time, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cfg = json.loads((ROOT / "config.json").read_text())
q, eta = cfg["q"], cfg["eta"]
b = cfg["wall"] - cfg["radius"]
keys = ("x", "v", "R", "W", "Q", "D", "A", "P", "S")

def initial(c):
    return dict(x=c["x"], v=c["v"], R=c["R"], W=0., Q=0., D=0., A=0., P=0., S=0., t=0., hits=[])

def inspect(s, c, worst):
    m = c["m"]
    assert all(math.isfinite(s[k]) for k in keys)
    assert s["R"] >= -1e-10 and c["R"]-s["R"] >= -1e-10
    assert s["x"] <= b+1e-10 and min(s["W"],s["Q"],s["D"]) >= -1e-10
    K, K0 = .5*m*s["v"]**2, .5*m*c["v"]**2
    vals = [
        abs(s["R"]+s["W"]/(eta*q)-c["R"])/max(1,c["R"]),
        abs(q*s["R"]+K+s["Q"]+s["D"]-q*c["R"]-K0)/max(1,q*c["R"]+K0),
        abs(m*s["v"]+s["S"]-m*c["v"])/max(1,abs(m*c["v"])),
        abs(K-K0-s["W"]+s["D"])/max(1,K0),
        abs(m*(s["v"]-c["v"])-s["A"]-s["P"])/max(1,abs(m*c["v"])),
        abs(s["S"]+s["A"]+s["P"])/max(1,abs(m*c["v"]))
    ]
    for i,v in enumerate(vals): worst[i]=max(worst[i],v)

def advance(s, c, h, F, worst):
    m, e = c["m"], c["e"]
    remaining=h
    if F>0 and s["R"]>0:
        assert s["v"]>=0
        if s["x"]==b and s["v"]==0:
            J=F*h
            s["A"]+=J; s["P"]-=J
            s["t"]+=h
            inspect(s,c,worst)
            return
        a=F/m
        full=s["v"]*h+.5*a*h*h
        limit=eta*q*s["R"]/F
        exhausted=limit<=full
        d=limit if exhausted else full
        assert s["x"]+d<b
        t=2*d/(s["v"]+math.sqrt(s["v"]**2+2*a*d)) if exhausted else h
        W=F*d; J=F*t
        s["x"]+=d; s["v"]+=a*t
        s["R"]=0. if exhausted else s["R"]-W/(eta*q)
        s["W"]+=W; s["Q"]+=(1/eta-1)*W
        s["A"]+=J; s["S"]-=J; s["t"]+=t
        remaining=h-t
        inspect(s,c,worst)
    if remaining>0:
        v=s["v"]
        if v>0 and s["x"]+v*remaining>=b:
            t=(b-s["x"])/v
            s["x"]=b; s["t"]+=t
            s["v"]=-e*v
            J=m*(s["v"]-v)
            s["P"]+=J; s["S"]-=J
            s["D"]+=.5*m*v*v*(1-e*e)
            s["hits"].append(s["t"])
            remaining-=t
            inspect(s,c,worst)
        s["x"]+=s["v"]*remaining; s["t"]+=remaining
    inspect(s,c,worst)

def reference(c):
    # Whole segments, independently of time stepping.
    s=initial(c); result=[]; m,e=c["m"],c["e"]
    for duration,F in c["segments"]:
        x,v,R=s["x"],s["v"],s["R"]
        if F and R and x==b and v==0:
            s["A"]+=F*duration; s["P"]-=F*duration
        else:
            drive=0.
            if F and R:
                a=F/m
                drive=min(duration,(math.sqrt(v*v+2*a*eta*q*R/F)-v)/a)
                dx=v*drive+a*drive**2/2
                W=F*dx
                s["R"]=R-W/(eta*q)
                s["W"]+=W; s["Q"]+=W/eta-W
                s["A"]+=F*drive
                x+=dx; v+=a*drive
            coast=duration-drive
            if v>0 and (b-x)/v<=coast:
                hit=(b-x)/v
                s["hits"].append(s["t"]+drive+hit)
                s["P"]-=m*(1+e)*v
                s["D"]+=.5*m*v*v-.5*m*(e*v)**2
                v=-e*v; x=b+v*(coast-hit)
            else:
                x+=v*coast
            s["x"],s["v"]=x,v
        s["S"]=-s["A"]-s["P"]
        s["t"]+=duration
        result.append(json.loads(json.dumps(s)))
    return result

def run(c,dt,replay=False):
    schedule=[(i,F,j==round(t/dt)-1) for i,(t,F) in enumerate(c["segments"]) for j in range(round(t/dt))]
    s=initial(c); worst=[0.]*6; checkpoints=[]; midpoint=None
    for n,(_,F,end) in enumerate(schedule):
        if n==len(schedule)//2: midpoint=json.dumps(s,sort_keys=True)
        advance(s,c,dt,F,worst)
        if end: checkpoints.append(json.loads(json.dumps(s)))
    equal=None
    if replay:
        z=json.loads(midpoint); w=[0.]*6
        for _,F,_ in schedule[len(schedule)//2:]: advance(z,c,dt,F,w)
        equal=json.dumps(z,sort_keys=True)==json.dumps(s,sort_keys=True)
    ref=reference(c)
    err=max(abs(a[k]-r[k]) for a,r in zip(checkpoints,ref) for k in keys)
    assert all(len(a["hits"])==len(r["hits"]) for a,r in zip(checkpoints,ref))
    hiterr=max([abs(t-u) for a,r in zip(checkpoints,ref) for t,u in zip(a["hits"],r["hits"])]+[0.])
    return dict(id=c["id"],dt=dt,steps=len(schedule),checkpoints=checkpoints,reference_error=max(err,hiterr),residuals=worst,replay=equal)

def close(a,b): return abs(a-b)<=1e-9

def main():
    start=time.perf_counter()
    runs=[run(c,dt,dt==cfg["steps"][-1]) for c in cfg["cases"] for dt in cfg["steps"]]
    fine={r["id"]:r for r in runs if r["dt"]==cfg["steps"][-1]}
    coarse={r["id"]:r for r in runs if r["dt"]==cfg["steps"][0]}
    f={k:r["checkpoints"][-1] for k,r in fine.items()}
    diff=max(abs(a[k]-z[k]) for name in fine for a,z in zip(fine[name]["checkpoints"],coarse[name]["checkpoints"]) for k in keys)
    residual=max(max(r["residuals"]) for r in runs)
    err=max(r["reference_error"] for r in runs)
    def check(name,expected): return all(close(f[name][k],v) for k,v in expected.items())
    criteria={
        "C1":True,
        "C2":residual<=1e-10,
        "C3":err<=1e-9,
        "C4":diff<=1e-9,
        "C5":check("no-command",dict(x=2,W=0,Q=0,R=1)) and check("no-fuel",dict(x=0,v=0,W=0,A=0)) and check("free",dict(x=2,v=2,W=4)) and check("load",dict(x=1,v=1,W=2)) and check("deplete",dict(R=0,W=.5)) and f["deplete"]["x"]>.25,
        "C6":check("elastic",dict(D=0,v=-2,x=2)) and check("inelastic",dict(D=3,v=-1,x=2.5)) and check("stall",dict(x=3,v=0,W=0,A=4,P=-4,S=0)) and all(len(f[k]["hits"])==1 and close(f[k]["hits"][0],1.5) for k in ("elastic","inelastic")),
        "C7":check("drive-coast",dict(W=1,D=.75,x=2.25,v=-.5)) and close(fine["drive-coast"]["checkpoints"][0]["R"],f["drive-coast"]["R"]),
        "C8":all(r["replay"] for r in fine.values())
    }
    elapsed=time.perf_counter()-start
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria["C9"]=elapsed<20 and rss<256
    data=dict(criteria=criteria,passed=all(criteria.values()),max_residual=residual,max_reference_error=err,max_refinement_difference=diff,runs=runs,elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ("run.py","config.json")})
    (ROOT/"results.json").write_text(json.dumps(data,separators=(",",":"),sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in data.items() if k!="runs"},sort_keys=True))
    print(json.dumps(f,sort_keys=True))
    if not data["passed"]: raise SystemExit(1)

if __name__=="__main__": main()
