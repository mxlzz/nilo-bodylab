"""E3-D01: local synthetic material damage, finite precursor and functional probe."""
import hashlib,json,math,platform,resource,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/"config.json").read_text())
m,cap,q,eta,p0,pm,gg,rc=(cfg[k] for k in ("m","capacity","q","eta","basal","patch_mass","patch_gamma","repair_cost"))
def init(c):
    active=list(c["initial"]); ef=[0. if a else c["E"][i] for i,a in enumerate(active)]
    return dict(active=active,ef=[0.,0.],fract_debris=sum(ef),debris=pm*active.count(False),P=c["P"],R=c["R"],S=cap-c["R"],X=cfg["refill_stock"],Z=0.,x=0.,v=0.,Wm=0.,Wb=0.,D=0.,Q=0.,basal=0.,miss=0.,repair_energy=0.,Jsub=0.,Jfix=0.,Jenv_sub=0.,Jenv_fix=0.,fixture_work=0.,mass_err=0.,energy_err=0.,mech_err=0.,identity_err=0.,momentum_err=0.,reaction_err=0.,minstock=0.,events=[],phases={},steps=0)
def fract(s):return s["fract_debris"]+sum(s["ef"])
def consume(s,e):
    s["R"]-=e/q;s["S"]+=e/q
def basal(s,dt):
    e=min(q*max(s["R"],0.),p0*dt);consume(s,e);s["Q"]+=e;s["basal"]+=e;s["miss"]+=p0*dt-e
def check(s,c):
    E0=q*(c["R"]+cfg["refill_stock"])+sum(c["E"][i] for i,a in enumerate(c["initial"]) if not a)
    A=pm*sum(s["active"]); Ef=fract(s);Ef0=E0-q*(c["R"]+cfg["refill_stock"])
    s["mass_err"]=max(s["mass_err"],abs(A+s["debris"]+s["P"]-(2*pm+c["P"])),abs(s["R"]+s["S"]-cap),abs(s["X"]+s["Z"]-cfg["refill_stock"]),abs(A+s["debris"]+s["P"]+s["R"]+s["S"]+(m-cap-2*pm-c["P"])-m))
    K=.5*m*s["v"]**2
    s["energy_err"]=max(s["energy_err"],abs(q*(s["R"]+s["X"])+K+s["Q"]+s["D"]+Ef-E0))
    s["mech_err"]=max(s["mech_err"],abs(K-s["Wb"]))
    s["identity_err"]=max(s["identity_err"],abs(s["Wm"]-s["Wb"]-s["D"]-(Ef-Ef0)))
    s["momentum_err"]=max(s["momentum_err"],abs(m*s["v"]-s["Jsub"]-s["Jfix"]))
    s["reaction_err"]=max(s["reaction_err"],abs(s["Jsub"]+s["Jenv_sub"]),abs(s["Jfix"]+s["Jenv_fix"]))
    s["minstock"]=min(s["minstock"],s["R"],s["S"],s["X"],s["Z"],s["P"],s["debris"],*s["ef"],s["fract_debris"])
    if not all(math.isfinite(s[k]) for k in ("R","S","P","x","v","Q","D","Wm","energy_err")):raise ValueError("nonfinite")
def phase(s):
    return dict(active=list(s["active"]),attached=pm*sum(s["active"]),debris=s["debris"],P=s["P"],R=s["R"],X=s["X"],S=s["S"],Z=s["Z"],fract=fract(s),Wm=s["Wm"],Wb=s["Wb"],D=s["D"],Q=s["Q"],basal=s["basal"],repair_energy=s["repair_energy"],x=s["x"],v=s["v"])
def step(s,c,dt,i,nT,nR,nP):
    if i==nT:
        s["phases"]["exposure"]=phase(s)
    if i==nT+nR:
        s["phases"]["repair"]=phase(s)
        before=(s["x"],s["v"]);u=min(s["S"],s["X"])
        s["R"]+=u;s["S"]-=u;s["X"]-=u;s["Z"]+=u
        assert (s["x"],s["v"])==before
        s["events"].append(dict(kind="refill",mass=u,time=(nT+nR)*dt))
        s["phases"]["probe_start"]=phase(s)
        check(s,c)
    basal(s,dt)
    g=gg*sum(s["active"]);U=eta*q*max(s["R"],0.)
    if i<nT:
        u=c["u"]
        if g and g*u*u*dt>U:u=math.sqrt(U/(g*dt))
        w=0.
        for k,a in enumerate(s["active"]):
            if not a:continue
            wi=gg*u*u*dt;w+=wi
            e=min(c["alpha"]*wi,max(0.,c["E"][k]-s["ef"][k]))
            s["ef"][k]+=e;s["D"]+=wi-e
            if s["ef"][k]>=c["E"][k]-1e-12:
                s["fract_debris"]+=s["ef"][k];s["ef"][k]=0.
                s["active"][k]=False;s["debris"]+=pm
                s["events"].append(dict(kind="fracture",slot=k,time=(i+1)*dt))
        consume(s,w/eta);s["Wm"]+=w;s["Q"]+=w*(1/eta-1)
        j=g*u*dt;s["Jsub"]+=j;s["Jfix"]-=j;s["Jenv_sub"]-=j;s["Jenv_fix"]+=j
    elif i<nT+nR:
        if c["repair"] and (i-nT+1)%round(cfg["repair_period"]/dt)==0:
            empty=[k for k,a in enumerate(s["active"]) if not a]
            if empty:
                why="material" if s["P"]<pm-1e-12 else ("energy" if q*s["R"]<rc-1e-12 else None)
                if why is None:
                    k=empty[0];s["active"][k]=True;s["P"]-=pm
                    consume(s,rc);s["Q"]+=rc;s["repair_energy"]+=rc
                    s["events"].append(dict(kind="repair",slot=k,time=(i+1)*dt,energy=rc,mass=pm))
                else:s["events"].append(dict(kind="reject",reason=why,time=(i+1)*dt))
    else:
        u=cfg["probe_u"];v=s["v"]
        if U<=1e-12:u=0.
        elif g and g*u*(u-v)*dt>U:u=(v+math.sqrt(v*v+4*U/(g*dt)))/2
        F=g*(u-v);w=F*u*dt;wb=F*v*dt;dis=g*(u-v)**2*dt
        assert w>=-1e-12 and dis>=0
        consume(s,w/eta);s["Q"]+=w*(1/eta-1);s["Wm"]+=w;s["Wb"]+=wb;s["D"]+=dis
        s["v"]+=F*dt/m;s["x"]+=s["v"]*dt;s["Jsub"]+=F*dt;s["Jenv_sub"]-=F*dt
    s["steps"]+=1;check(s,c)
def reference(c):
    active=list(c["initial"]);fracture=[];W=0.;ef=sum(c["E"][k] for k,a in enumerate(active) if not a);debris=pm*active.count(False)
    for k,a in enumerate(active):
        if not a:continue
        p=gg*c["u"]**2;rate=c["alpha"]*p
        tf=c["E"][k]/rate if rate else math.inf
        w=p*min(c["T"],tf);W+=w;ef+=min(c["E"][k],c["alpha"]*w)
        if tf<=c["T"]+1e-12:
            active[k]=False;debris+=pm;fracture.append([k,tf])
    n_exp=sum(active);debris_exp=debris;R=c["R"]-(W/eta+p0*c["T"])/q
    P=c["P"];spent=0.;rejections=[]
    for _ in range(round(cfg["repair_duration"]/cfg["repair_period"])):
        R=max(0.,R-p0*cfg["repair_period"]/q)
        if c["repair"] and not all(active):
            if P<pm-1e-12:rejections.append("material")
            elif q*R<rc-1e-12:rejections.append("energy")
            else:
                active[active.index(False)]=True;P-=pm;R-=rc/q;spent+=rc
    k=gg*sum(active)/m;u=cfg["probe_u"];L=cfg["probe_duration"]
    v=u*(1-math.exp(-k*L)) if k else 0.
    x=u*(L-(1-math.exp(-k*L))/k) if k else 0.
    wp=m*u*u*(1-math.exp(-k*L)) if k else 0.
    return dict(fractures=fracture,Wexp=W,fract=ef,n_exp=n_exp,debris_exp=debris_exp,n_repaired=sum(active),P=P,repair_energy=spent,rejections=rejections,x=x,v=v,Wprobe=wp,R_final=cap-(p0*L+wp/eta)/q)
def run(c,dt,replay):
    nT=round(c["T"]/dt);nR=round(cfg["repair_duration"]/dt);nP=round(cfg["probe_duration"]/dt);N=nT+nR+nP
    s=init(c);snap=None;split=max(1,nT//2) if nT else nR//2
    for i in range(N):
        step(s,c,dt,i,nT,nR,nP)
        if replay and i+1==split:snap=json.loads(json.dumps(s))
    s["phases"]["probe_end"]=phase(s)
    exact=None
    if replay:
        assert snap is not None
        for i in range(split,N):step(snap,c,dt,i,nT,nR,nP)
        snap["phases"]["probe_end"]=phase(snap);exact=snap==s
    ref=reference(c);p=s["phases"]; actual={e["slot"]:e["time"] for e in s["events"] if e["kind"]=="fracture"}
    expected=dict(ref["fractures"])
    timing=max([abs(actual[k]-v) for k,v in expected.items() if k in actual]+[0.])
    err=dict(Wexp=abs(p["exposure"]["Wm"]-ref["Wexp"]),fract=abs(p["exposure"]["fract"]-ref["fract"]),x=abs(s["x"]-ref["x"]),v=abs(s["v"]-ref["v"]),Wprobe=abs(s["Wm"]-p["probe_start"]["Wm"]-ref["Wprobe"]),R=abs(s["R"]-ref["R_final"]))
    material=max(abs(p["exposure"]["attached"]-pm*ref["n_exp"]),abs(p["exposure"]["debris"]-ref["debris_exp"]),abs(p["repair"]["attached"]-pm*ref["n_repaired"]),abs(p["repair"]["P"]-ref["P"]),abs(p["repair"]["debris"]-ref["debris_exp"]),abs(p["repair"]["repair_energy"]-ref["repair_energy"]),abs(p["repair"]["fract"]-p["exposure"]["fract"]))
    return dict(type="dynamic",id=c["id"],dt=dt,steps=N,final=s,reference=ref,errors=err,fracture_events_match=set(actual)==set(expected),fracture_time_error=timing,material_error=material,rejections_match=[e["reason"] for e in s["events"] if e["kind"]=="reject"]==ref["rejections"],replay_exact=exact)
def main():
    start=time.perf_counter()
    import sys
    assert sys.version_info[:2]==(3,12)
    rs=[run(c,dt,dt==cfg["dt"][-1]) for c in cfg["cases"] for dt in cfg["dt"]]
    fine=[a for a in rs if a["dt"]==cfg["dt"][-1]];f={a["id"]:a["final"] for a in fine}
    maxall=lambda k:max(a["final"][k] for a in rs);maxfine=lambda k:max(a["final"][k] for a in fine)
    C1=min(a["final"]["minstock"] for a in rs)>=-1e-9 and maxall("mass_err")<=1e-9 and max(maxall("energy_err"),maxall("mech_err"))<=.03 and max(maxfine("energy_err"),maxfine("mech_err"))<=.01 and maxall("identity_err")<=1e-9 and maxall("momentum_err")<=1e-9 and maxall("reaction_err")<=1e-9 and maxall("fixture_work")==0
    conv=[max(max(a["errors"][k] for k in ("Wexp","x","v","Wprobe")) for a in rs if a["dt"]==dt) for dt in cfg["dt"]]
    C2=all(a["fracture_events_match"] and a["fracture_time_error"]<=2*a["dt"]+1e-9 and max(a["errors"]["Wexp"],a["errors"]["fract"])<=.02 for a in rs) and all(max(a["errors"]["Wexp"],a["errors"]["fract"])<=.005 for a in fine) and conv[-1]<=.65*conv[0]+1e-9
    C3=all(a["material_error"]<=1e-9 and a["rejections_match"] for a in rs) and all(e["reason"]=="energy" for e in f["no-energy"]["events"] if e["kind"]=="reject") and all(e["reason"]=="material" for e in f["total"]["events"] if e["kind"]=="reject")
    C4=all(abs(a["final"]["phases"]["probe_start"]["R"]-cap)<=1e-9 and a["final"]["phases"]["probe_start"]["x"]==a["final"]["phases"]["probe_start"]["v"]==0 and abs(a["final"]["phases"]["probe_start"]["X"]+a["final"]["phases"]["probe_start"]["Z"]-cfg["refill_stock"])<=1e-9 for a in rs) and all(max(a["errors"][k] for k in ("x","v","Wprobe"))<=.003 and a["errors"]["R"]<=.001 for a in fine)
    C5=f["intact"]["x"]>f["partial"]["x"]>.05 and f["intact"]["x"]-f["partial"]["x"]>=.05 and all(abs(f[k]["x"])<=1e-9 for k in ("total","no-energy")) and all(abs(f[k]["x"]-f["intact"]["x"])<=1e-9 for k in ("partial-repair","total-repair","reserved")) and abs(f["one-repair"]["x"]-f["partial"]["x"])<=1e-9
    C6=all(a["final"]["phases"]["exposure"]["x"]==a["final"]["phases"]["exposure"]["v"]==0 and abs(a["final"]["phases"]["exposure"]["Wm"]-a["final"]["phases"]["exposure"]["D"]-(a["final"]["phases"]["exposure"]["fract"]-sum(c["E"][i] for i,b in enumerate(c["initial"]) if not b)))<=1e-9 for a in rs for c in cfg["cases"] if c["id"]==a["id"]) and f["intact"]["phases"]["exposure"]["fract"]==f["idle"]["phases"]["exposure"]["fract"]==0 and f["idle"]["phases"]["exposure"]["Wm"]==0 and f["intact"]["phases"]["exposure"]["Wm"]>0 and f["idle"]["basal"]>0
    C7=all(a["replay_exact"] for a in fine)
    elapsed=time.perf_counter()-start;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria={f"C{i+1}":bool(v) for i,v in enumerate((C1,C2,C3,C4,C5,C6,C7,elapsed<10 and rss<128))}
    sm=dict(type="summary",criteria=criteria,passed=all(criteria.values()),runs=len(rs),steps=sum(a["steps"] for a in rs),max_mass=maxall("mass_err"),max_energy=maxall("energy_err"),max_energy_fine=maxfine("energy_err"),max_mechanical=maxall("mech_err"),max_momentum=maxall("momentum_err"),max_identity=maxall("identity_err"),convergence=conv,elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("run.py","config.json")})
    lines=[json.dumps(a,separators=(",",":"),sort_keys=True,allow_nan=False) for a in [sm]+rs];raw="\n".join(lines)+"\n"
    (ROOT/"results.jsonl").write_text(raw);print("RESULT_SHA256="+hashlib.sha256(raw.encode()).hexdigest(),flush=True)
    for line in lines:print("RESULT_LINE="+line,flush=True)
    if not sm["passed"]:raise SystemExit(1)
if __name__=="__main__":main()
