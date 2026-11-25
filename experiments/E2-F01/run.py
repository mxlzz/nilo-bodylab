import argparse, hashlib, json, math, platform, resource, sys, time
from pathlib import Path

def initial(c,k):
    return dict(M=c["fuel"],W=0.,L=0.,H=k["C"]*c["T"],B=0.)

def probe(T,a,k):
    return k["K"]*4*(k["V"]-k["K"]*4)/(k["R0"]*(1+a*(T-k["Tref"])))

def run(c,a,dt,k,snap=None,start=0):
    s=initial(c,k) if snap is None else dict(snap)
    q,C,G=k["q"],k["C"],k["G"]
    E0=q*c["fuel"]+C*c["T"]
    balance=[0.,0.]
    valid=True
    ends=[]
    steps=0
    for dur,Ta,on,omega in c["segments"][start:]:
        n=round(dur/dt)
        assert n*dt==dur
        for _ in range(n):
            T=s["H"]/C
            R=k["R0"]*(1+a*(T-k["Tref"]))
            emf=k["K"]*omega
            I=(k["V"]-emf)/R if on else 0.
            pin=k["V"]*I
            pw=emf*I
            ph=I*I*R
            want=pin*dt/q
            m=min(s["M"],want)
            consumed=q*m
            work=consumed*pw/pin if pin else 0.
            heat=consumed*ph/pin if pin else 0.
            b=G*(T-Ta)*dt
            s["M"]-=m
            s["W"]+=m
            s["L"]+=work
            s["H"]+=heat-b
            s["B"]+=b
            balance[0]=max(balance[0],abs(s["M"]+s["W"]-c["fuel"])/max(1,c["fuel"]))
            balance[1]=max(balance[1],abs(q*s["M"]+s["L"]+s["H"]+s["B"]-E0)/max(1,E0))
            valid &= R>0 and 280<=s["H"]/C<=380 and min(s["M"],s["W"],s["L"])>=0 and 0<=m<=want and abs(pin-pw-ph)<=1e-10
            steps+=1
        ends.append(dict(s=dict(s),T=s["H"]/C,probe=probe(s["H"]/C,a,k)))
    return dict(ends=ends,balance=balance,valid=valid,steps=steps)

def reference(c,a,k):
    T,L=c["T"],0.
    ends=[]
    for dur,Ta,on,w in c["segments"]:
        if not a or not on:
            I=(k["V"]-k["K"]*w)/k["R0"] if on else 0.
            ph=I*I*k["R0"]
            eq=Ta+ph/k["G"]
            T=eq+(T-eq)*math.exp(-k["G"]*dur/k["C"])
            L+=k["K"]*w*I*dur
        else:
            def derivative(z):
                R=k["R0"]*(1+a*(z-k["Tref"]))
                i=(k["V"]-k["K"]*w)/R
                return (i*i*R-k["G"]*(z-Ta))/k["C"],k["K"]*w*i
            h=1/4096
            for _ in range(round(dur/h)):
                x,u=derivative(T)
                y,v=derivative(T+h*x/2)
                z,w2=derivative(T+h*y/2)
                r,j=derivative(T+h*z)
                T+=h*(x+2*y+2*z+r)/6
                L+=h*(u+2*v+2*w2+j)/6
        ends.append(dict(T=T,L=L))
    return ends

def main():
    begin=time.perf_counter()
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    data=Path(args.config).read_bytes()
    k=json.loads(data)
    lim=k["limits"]
    fine=min(k["dt"])
    records=[]
    for c in k["cases"]:
        for a in (0.,k["alpha"]):
            ref=reference(c,a,k) if c["id"]!="depletion" else None
            for dt in k["dt"]:
                z=run(c,a,dt,k)
                errT=max(abs(x["T"]-y["T"]) for x,y in zip(z["ends"],ref)) if ref else None
                errL=max(abs(x["s"]["L"]-y["L"])/max(1,abs(y["L"])) for x,y in zip(z["ends"],ref)) if ref else None
                replay=None
                if dt==fine and len(c["segments"])>1:
                    snap=json.loads(json.dumps(z["ends"][0]["s"]))
                    replay=run(c,a,dt,k,snap,1)["ends"]==z["ends"][1:]
                records.append(dict(id=c["id"],alpha=a,dt=dt,errT=errT,errL=errL,replay=replay,ref=ref,initial_probe=probe(c["T"],a,k),**z))
    f={(z["id"],z["alpha"]):z for z in records if z["dt"]==fine}
    def get(id,a,i=-1):
        return f[id,a]["ends"][i]
    def err(dt,field):
        return max(z[field] for z in records if z["dt"]==dt and z[field] is not None)
    a=k["alpha"]
    fineT,coarseT=err(fine,"errT"),err(2*fine,"errT")
    balance=max(max(z["balance"]) for z in records)
    cases={c["id"]:c for c in k["cases"]}
    histories={v:1-f["history-hot",v]["initial_probe"]/f["history-cold",v]["initial_probe"] for v in (0.,a)}
    recovery=[get("load-rest-load",a,i)["probe"] for i in (0,1,2)]
    control=[get("load-rest-load",0.,i)["probe"] for i in (0,1,2)]
    eps=1e-10
    def controls(v):
        rest=get("rest",v)
        stall=get("stall",v,0)
        d1,d2=get("depletion",v,0),get("depletion",v)
        return rest["s"]["M"]==20 and rest["s"]["L"]==0 and rest["T"]<330 and stall["s"]["L"]==0 and stall["T"]>300 and d1["s"]["M"]==0 and d2["s"]["M"]==0 and abs(d1["s"]["L"]-4)<=eps and d1["s"]["L"]==d2["s"]["L"]
    wall=time.perf_counter()-begin
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    checks=dict(balance_domain=balance<=lim["balance"] and all(z["valid"] for z in records),finite_flows=all(z["valid"] for z in records),reference=fineT<=lim["T_K"] and err(fine,"errL")<=lim["work_rel"],convergence=fineT<=lim["conv"]*coarseT or max(fineT,coarseT)<=1e-8,controls=all(controls(v) for v in (0.,a)),history=histories[a]>=lim["history_rel"] and histories[0.]==0,recovery=recovery[0]<recovery[1]<f["load-rest-load",a]["initial_probe"] and len(set(control))==1,replay=all(z["replay"] is True for z in f.values() if len(cases[z["id"]]["segments"])>1),resources=wall<=lim["wall_s"] and rss<=lim["rss_MiB"])
    out=dict(summary=dict(checks=checks,verdict="H1_conditional" if all(checks.values()) else "inconclusive",runs=len(records),steps=sum(z["steps"] for z in records),balance=balance,fine_error_K=fineT,coarse_error_K=coarseT,work_error=err(fine,"errL"),history_reduction=histories[a],recovery_probe_W=recovery,control_probe_W=control,wall_s=wall,rss_MiB=rss,python=sys.version,platform=platform.platform(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=hashlib.sha256(data).hexdigest()),records=records)
    Path(args.out).write_text(json.dumps(out,separators=(",",":"),allow_nan=False)+"\n")
    print(json.dumps(out["summary"],indent=2))
    return 0 if all(checks.values()) else 1

if __name__=="__main__":
    raise SystemExit(main())
