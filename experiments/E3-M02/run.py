import copy, hashlib, importlib.metadata, json, math, platform, resource, time
from pathlib import Path
import numpy as np
import mujoco as mj

ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/"config.json").read_text())
q,eta=cfg["q"],cfg["eta"]
b=cfg["wall"]-cfg["radius"]
sig=mj.mjtState.mjSTATE_INTEGRATION
keys=("x","v","W","R")

def build(c,dt):
    sr=" ".join(map(str,cfg["contact"]["solref"]))
    si=" ".join(map(str,cfg["contact"]["solimp"]))
    xml=f"""<mujoco model="restricted-reference">
      <compiler angle="radian"/>
      <option timestep="{dt}" gravity="0 0 0" integrator="Euler" solver="Newton" iterations="100" tolerance="1e-12"/>
      <default><geom condim="1" margin="0" gap="0" solref="{sr}" solimp="{si}"/></default>
      <worldbody>
        <geom name="wall" type="box" pos="{cfg['wall']+.25} 0 0" size=".25 2 2"/>
        <body name="body">
          <joint type="slide" axis="1 0 0" limited="false" damping="0" frictionloss="0" armature="0"/>
          <geom name="body" type="sphere" size="{cfg['radius']}" mass="{c['m']}"/>
        </body>
      </worldbody>
    </mujoco>"""
    m=mj.MjModel.from_xml_string(xml)
    assert m.nq==m.nv==1 and abs(m.body_mass[1]-c["m"])<=1e-12
    d=mj.MjData(m)
    d.qpos[0]=c["x"]; d.qvel[0]=c["v"]
    mj.mj_forward(m,d)
    return m,d

def ledger(c):
    return dict(U=eta*q*c["R"],W=0.,Q=0.,C=0.,Jact=0.,Jwall=0.,positive_impulse=0.,max_pen=0.,onset=None,contact_steps=0,mass_err=0.,momentum_err=0.,energy_err=0.,work_err=0.)

def advance(m,d,L,c,F,dt):
    mj.mj_step1(m,d)
    assert d.nefc==d.ncon
    x,v=float(d.qpos[0]),float(d.qvel[0])
    ncon=int(d.ncon); t=float(d.time)
    if ncon:
        L["contact_steps"]+=1
        if L["onset"] is None: L["onset"]=t
    if L["U"]<=1e-12: F=0.
    if F:
        assert v>=0 and ncon==0
        u=L["U"]; a=v*dt
        F=min(F,2*u/(a+math.sqrt(a*a+4*dt*dt*u/c["m"])))
    d.qfrc_applied[0]=F
    mj.mj_step2(m,d)
    xn,vn=float(d.qpos[0]),float(d.qvel[0])
    fc=float(d.qfrc_constraint[0])
    dx=xn-x; W=F*dx
    L["U"]-=W; L["W"]+=W; L["Q"]+=(1/eta-1)*W; L["C"]+=fc*dx
    L["Jact"]+=F*dt; L["Jwall"]+=fc*dt
    L["positive_impulse"]+=max(0.,fc*dt)
    L["max_pen"]=max(L["max_pen"],xn-b)
    mass=c["m"]; K=.5*mass*vn*vn; K0=.5*mass*c["v"]**2
    R=L["U"]/(eta*q)
    L["mass_err"]=max(L["mass_err"],abs(R+L["W"]/(eta*q)-c["R"]))
    L["momentum_err"]=max(L["momentum_err"],abs(mass*(vn-c["v"])-L["Jact"]-L["Jwall"]),abs(mass*vn-L["Jact"]-L["Jwall"]-mass*c["v"]))
    L["energy_err"]=max(L["energy_err"],abs(q*R+K+L["Q"]-L["C"]-q*c["R"]-K0))
    L["work_err"]=max(L["work_err"],abs(K-K0-L["W"]-L["C"]))
    assert math.isfinite(xn) and math.isfinite(vn) and all(math.isfinite(z) for z in L.values() if z is not None)
    assert L["U"]>=-1e-9 and L["mass_err"]<=1e-9 and W>=-1e-10
    return ncon

def state(m,d):
    z=np.empty(mj.mj_stateSize(m,sig),dtype=np.float64)
    mj.mj_getState(m,d,z,sig)
    return z

def checkpoint(d,L,c):
    return dict(x=float(d.qpos[0]),v=float(d.qvel[0]),R=L["U"]/(eta*q),K=.5*c["m"]*float(d.qvel[0])**2,**L)

def run(c,dt,replay):
    m,d=build(c,dt); L=ledger(c)
    schedule=[(F,j==round(t/dt)-1) for t,F in c["segments"] for j in range(round(t/dt))]
    checkpoints=[]; snap=None; contact="contact_time" in c
    for i,(F,end) in enumerate(schedule):
        ncon=advance(m,d,L,c,F,dt)
        if replay and snap is None and ((contact and ncon>0) or (not contact and i==len(schedule)//2-1)):
            snap=(i+1,state(m,d).tolist(),json.loads(json.dumps(L)))
        if end: checkpoints.append(checkpoint(d,L,c))
    replay_error=None; replay_contact=None
    if replay:
        assert snap is not None and snap[0]<len(schedule)
        i,z,L2=snap
        d2=mj.MjData(m)
        mj.mj_setState(m,d2,np.asarray(z,dtype=np.float64),sig)
        for j,(F,_) in enumerate(schedule[i:]):
            n=advance(m,d2,L2,c,F,dt)
            if j==0: replay_contact=bool(n)
        errs=[abs(float(L[k])-float(L2[k])) if L[k] is not None and L2[k] is not None else (0. if L[k]==L2[k] else 1.) for k in L]
        replay_error=max(float(np.max(np.abs(state(m,d)-state(m,d2)))),max(errs))
    return dict(id=c["id"],dt=dt,steps=len(schedule),checkpoints=checkpoints,replay_error=replay_error,replay_contact=replay_contact)

def main():
    start=time.perf_counter()
    assert importlib.metadata.version("mujoco-core")=="4.0.1" and mj.mj_versionString()=="4.0.1" and np.__version__=="2.3.5"
    cases={c["id"]:c for c in cfg["cases"]}
    runs=[run(c,dt,dt==cfg["steps"][-1]) for c in cfg["cases"] for dt in cfg["steps"]]
    fine={r["id"]:r for r in runs if r["dt"]==cfg["steps"][-1]}
    coarse={r["id"]:r for r in runs if r["dt"]==cfg["steps"][0]}
    f={k:r["checkpoints"][-1] for k,r in fine.items()}
    def referr(r):
        c=cases[r["id"]]
        if "reference" in c: ref=c["reference"]; cp=r["checkpoints"][-1]
        elif "first_reference" in c: ref=c["first_reference"]; cp=r["checkpoints"][0]
        else: return [0.]*4
        return [abs(cp[k]-v) for k,v in zip(keys,ref)]
    errors=[referr(r) for r in fine.values()]
    ef=[max(e[i] for e in errors) for i in range(4)]
    fine_nc=max(max(referr(r)[:3]) for k,r in fine.items() if "reference" in cases[k])
    coarse_nc=max(max(referr(r)[:3]) for k,r in coarse.items() if "reference" in cases[k])
    allmax=lambda k:max(r["checkpoints"][-1][k] for r in runs)
    max_energy_f=max(max(x["energy_err"],x["work_err"]) for x in f.values())
    max_energy_all=max(allmax("energy_err"),allmax("work_err"))
    def zero(x): return abs(x)<=1e-10
    contact_ok=True
    for r in runs:
        c=cases[r["id"]]; x=r["checkpoints"][-1]
        if "contact_time" in c:
            contact_ok &= x["contact_steps"]>0 and x["positive_impulse"]<=1e-10 and x["max_pen"]<=.05 and x["K"]<=c["precontact_K"]+.05 and x["C"]<=.05
            if r["dt"]==cfg["steps"][-1]: contact_ok &= abs(x["onset"]-c["contact_time"])<=.003
            if r["id"]=="drive-coast":
                cp=r["checkpoints"][0]
                contact_ok &= zero(x["W"]-cp["W"]) and zero(x["Jact"]-cp["Jact"])
            else: contact_ok &= zero(x["W"]) and zero(x["Jact"])
        else: contact_ok &= x["contact_steps"]==0
    criteria={
        "C1":allmax("mass_err")<=1e-9,
        "C2":allmax("momentum_err")<=1e-8 and max_energy_f<=.05 and max_energy_all<=.20,
        "C3":all(e<=t for e,t in zip(ef,[.01,.01,.02,.004])) and fine_nc<=.65*coarse_nc+1e-9,
        "C4":all(zero(f[k]["W"]) and zero(f[k]["Jact"]) for k in ("no-command","no-fuel")) and zero(f["no-fuel"]["x"]) and zero(f["no-fuel"]["v"]) and all(f[k]["U"]<=1e-9 and abs(f[k]["W"]-w)<=1e-9 and f[k]["v"]>0 for k,w in (("deplete",.5),("reserved",.35))) and all(abs(f[k]["Jact"]-4)<=1e-8 for k in ("free","load")) and f["load"]["x"]<f["free"]["x"],
        "C5":bool(contact_ok),
        "C6":all(r["replay_error"]<=1e-12 and (r["replay_contact"] if "contact_time" in cases[k] else True) for k,r in fine.items())
    }
    elapsed=time.perf_counter()-start
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria["C7"]=elapsed<20 and rss<512
    data=dict(criteria=criteria,passed=all(criteria.values()),fine_reference_errors=dict(zip(keys,ef)),max_nc_error_fine=fine_nc,max_nc_error_coarse=coarse_nc,max_energy_fine=max_energy_f,max_energy_all=max_energy_all,max_momentum=allmax("momentum_err"),max_mass=allmax("mass_err"),max_penetration=allmax("max_pen"),runs=runs,elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),mujoco=mj.mj_versionString(),numpy=np.__version__,sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("run.py","config.json","requirements.txt")})
    raw=json.dumps(data,separators=(",",":"),sort_keys=True,allow_nan=False)+"\n"
    (ROOT/"results.json").write_text(raw)
    print("RESULT_SHA256="+hashlib.sha256(raw.encode()).hexdigest(),flush=True)
    print("RESULT_JSON="+raw.strip(),flush=True)
    if not data["passed"]: raise SystemExit(1)

if __name__=="__main__": main()
