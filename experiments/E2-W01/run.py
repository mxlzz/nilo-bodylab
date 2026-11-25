import argparse, hashlib, importlib.util, json, math, platform, resource, sys, time
from pathlib import Path

E1=Path(__file__).resolve().parent.parent/"E1-01"/"run.py"
assert hashlib.sha256(E1.read_bytes()).hexdigest()=="2777c4765618eb68d404657bf8fa4d3f7060adebdd59b8039ca66c9d4d509932"
spec=importlib.util.spec_from_file_location("e1", E1)
e1=importlib.util.module_from_spec(spec)
spec.loader.exec_module(e1)

def initial(c,k):
    return dict(f=e1.initial(c,c["model"]),m=c["m"],x=c["x"],v=0.,H=(k["Cd"]+k["cp"]*c["m"])*(c["T"]-k["Tr"]),B=0.,U=0.)

def temp(s,k):
    return k["Tr"]+s["H"]/(k["Cd"]+k["cp"]*s["m"])

def exact(T,m,t,r,p,Ta,G,L,k):
    cp,Cd=k["cp"],k["Cd"]
    wet=min(t,m/r) if r else 0.
    if wet:
        C0=Cd+cp*m
        lost=min(m,r*wet)
        C1=Cd+cp*(m-lost)
        if G:
            eq=Ta+(p-L*r)/G
            T=eq+(T-eq)*(C1/C0)**(G/(cp*r))
        else:
            T+=(p-L*r)*math.log(C0/C1)/(cp*r)
        m-=lost
    dry=t-wet
    if dry:
        C=Cd+cp*m
        if G:
            eq=Ta+p/G
            T=eq+(T-eq)*math.exp(-G*dry/C)
        else:
            T+=p*dry/C
    return T,m

def simulate(c,phase,dt,k,checkpoint=None,start=0):
    cp,Tr,q=k["cp"],k["Tr"],k["q"]
    L=k["Lv"] if phase=="EVAP" else 0.
    s=initial(c,k) if checkpoint is None else json.loads(json.dumps(checkpoint))
    n0=initial(c,k)
    def totals(a):
        f=a["f"]
        return (f["X"]+f["P"]+f["R"]+f["W"]+1.,a["m"]+a["x"]+a["v"],q*(f["X"]+f["P"]+f["R"])+f["L"]+a["H"]+a["B"]+a["U"]+cp*a["x"]*(c["Tin"]-Tr))
    origins=totals(n0)
    errors=[0.,0.,0.]
    valid=True
    def inspect():
        nonlocal valid
        for j,z in enumerate(totals(s)):
            scale=max(1e-6 if j==1 else 1.,abs(origins[j]))
            errors[j]=max(errors[j],abs(z-origins[j])/scale)
        valid &= all(s[z]>=0 for z in ("m","x","v")) and all(s["f"][z]>=0 for z in ("X","P","R","W"))
        valid &= 285<=temp(s,k)<=320
    refT,refm,refx=temp(s,k),s["m"],s["x"]
    ends=[]
    steps=0
    inspect()
    for dur,Ta,a,b,r,request in c["segments"][start:]:
        u=min(request,s["x"])
        s["x"]-=u
        s["m"]+=u
        s["H"]+=cp*u*(c["Tin"]-Tr)
        ru=min(request,refx)
        refT=((k["Cd"]+cp*refm)*refT+cp*ru*c["Tin"])/(k["Cd"]+cp*(refm+ru))
        refm+=ru
        refx-=ru
        inspect()
        n=round(dur/dt)
        assert n*dt==dur
        p=q*(a+b*(1-k["eta"]))
        if c["model"]=="A0":
            refT,refm=exact(refT,refm,dur,r,p,Ta,c["G"],L,k)
        for _ in range(n):
            T=temp(s,k)
            old=s["f"]["Q"]
            e1.step(s["f"],dict(maintenance=a,activity=b),c["model"],c["k"],dt,q,k["eta"])
            g=s["f"]["Q"]-old
            if c["model"]=="A0":
                valid &= abs(g-p*dt)<=1e-9
            else:
                refT,refm=exact(refT,refm,dt,r,g/dt,Ta,c["G"],L,k)
            loss=min(s["m"],r*dt)
            exchange=c["G"]*(T-Ta)*dt
            export=loss*(cp*(T-Tr)+L)
            s["H"]+=g-exchange-export
            s["B"]+=exchange
            s["U"]+=export
            s["m"]-=loss
            s["v"]+=loss
            valid &= 0<=loss<=r*dt and 0<=u<=request
            inspect()
            steps+=1
        ends.append(dict(state=json.loads(json.dumps(s)),T=temp(s,k),refT=refT,refm=refm,accepted=u,rejected=request-u))
    return dict(ends=ends,balances=errors,valid=valid,steps=steps)

def main():
    t=time.perf_counter()
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    k=json.loads(Path(args.config).read_text())
    runs=[]
    fine=k["dt"][-1]
    replay=True
    for dt in k["dt"]:
        for c in k["cases"]:
            for phase in ("EVAP","DRAIN"):
                z=simulate(c,phase,dt,k)
                if dt==fine:
                    r=simulate(c,phase,dt,k,z["ends"][0]["state"],1)
                    replay &= [x["state"] for x in r["ends"]]==[x["state"] for x in z["ends"][1:]]
                runs.append(dict(case=c["id"],phase=phase,dt=dt,**z))
    def error(dt):
        return max(abs(x["T"]-x["refT"]) for z in runs if z["dt"]==dt for x in z["ends"])
    f={(z["case"],z["phase"]):z["ends"] for z in runs if z["dt"]==fine}
    def end(c,p,i=-1): return f[c,p][i]
    def same(c):
        return all(abs(a["T"]-b["T"])<=1e-10 for a,b in zip(f[c,"EVAP"],f[c,"DRAIN"]))
    mx=[max(z["balances"][i] for z in runs) for i in range(3)]
    fe,co=error(fine),error(k["dt"][-2])
    me=max(abs(x["state"]["m"]-x["refm"]) for z in runs if z["dt"]==fine for x in z["ends"])
    ex1,ex2=end("exhausted","EVAP",0),end("exhausted","EVAP")
    mix=( (k["Cd"]+k["cp"]*.002)*310+k["cp"]*.002*290)/(k["Cd"]+k["cp"]*.004)
    wetE,wetD=end("wet","EVAP",0),end("wet","DRAIN",0)
    wall=time.perf_counter()-t
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    checks=[
        mx[0]<=1e-10,mx[1]<=1e-10,mx[2]<=1e-10,all(z["valid"] for z in runs),
        fe<=.05 and me<=1e-12,fe<=.65*co or max(fe,co)<=1e-8,replay,
        all(same(c) and all(end(c,p)["state"]["v"]==0 for p in ("EVAP","DRAIN")) for c in ("sealed","dry")),
        same("mix") and all(abs(end("mix",p)["T"]-mix)<=1e-10 for p in ("EVAP","DRAIN")),
        wetD["T"]-wetE["T"]>=2 and abs(wetD["state"]["v"]-wetE["state"]["v"])<=1e-12,
        ex1["state"]["m"]<=1e-12 and ex2["state"]["v"]==ex1["state"]["v"] and ex2["state"]["U"]==ex1["state"]["U"] and ex2["T"]>ex1["T"],
        all(end("refill",p)["state"]["x"]<=1e-12 and end("refill",p)["rejected"]>0 for p in ("EVAP","DRAIN")),
        all(end("combined",p)["state"]["f"]["L"]>0 and end("combined",p)["state"]["v"]>0 for p in ("EVAP","DRAIN")),
        wall<=20 and rss<=128]
    summary=dict(checks=checks,passed=sum(checks),runs=len(runs),steps=sum(z["steps"] for z in runs),balances=mx,fine_error_K=fe,previous_error_K=co,water_error_kg=me,wet_delta_K=wetD["T"]-wetE["T"],wall_s=wall,rss_MiB=rss,python=sys.version,platform=platform.platform(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=hashlib.sha256(Path(args.config).read_bytes()).hexdigest())
    Path(args.out).write_text(json.dumps(dict(summary=summary,runs=runs),separators=(",",":"))+"\n")
    print(json.dumps(summary))
    sys.exit(0 if all(checks) else 1)

if __name__=="__main__":
    main()
