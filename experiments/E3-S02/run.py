import hashlib, importlib.metadata, json, math, platform, resource, time
from pathlib import Path
import numpy as np
import mujoco as mj

ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/"config.json").read_text())
r,m,M,period,duration=(cfg[k] for k in ("radius","m","M","period","duration"))
sig=mj.mjtState.mjSTATE_INTEGRATION
mass=np.array([m,m,M,M])
def build(c,dt,sensor):
    wall=""
    if c["wall"] is not None:
        x,y=c["wall"]
        if c["axis"]=="x": x+=r+.1; size=".1 .6 .5"
        else: y+=r+.1; size=".6 .1 .5"
        wall=f'<geom name="wall" type="box" pos="{x} {y} 0" size="{size}"/>'
    site='<site name="skin" type="sphere" size=".26" pos="0 0 0"/>' if sensor else ''
    sense='<sensor><touch name="touch" site="skin"/></sensor>' if sensor else ''
    def body(name,x,mm,extra):
        return f'<body name="{name}" pos="{x} 0 0"><joint type="slide" axis="1 0 0" damping="0" armature="0" frictionloss="0"/><joint type="slide" axis="0 1 0" damping="0" armature="0" frictionloss="0"/><geom name="{name}" type="sphere" size="{r}" mass="{mm}"/>{extra}</body>'
    xml=f'<mujoco><option timestep="{dt}" gravity="0 0 0" integrator="Euler" solver="Newton" iterations="100" tolerance="1e-12"/><default><geom condim="1" margin="0" gap="0" solref="{cfg["solref"]}" solimp="{cfg["solimp"]}"/></default><worldbody>{wall}{body("body",0,m,site)}{body("counter",2,M,"")}</worldbody>{sense}</mujoco>'
    a=mj.MjModel.from_xml_string(xml); d=mj.MjData(a)
    d.qvel[:]=c["body_v"]+c["counter_v"]; mj.mj_forward(a,d)
    assert a.nq==a.nv==4 and abs(a.body_mass[1]-m)<1e-12 and abs(a.body_mass[2]-M)<1e-12
    assert a.nsensordata==int(sensor)
    return a,d
def state(a,d):
    v=np.empty(mj.mj_stateSize(a,sig)); mj.mj_getState(a,d,v,sig); return v
def ke(v): return .5*float(np.dot(mass,v*v))
def init(d):
    return dict(pending=0.,last=0.,total=0.,start_v=d.qvel.tolist(),J=[0.,0.],onset=None,pen=0.,minforce=0.,momentum_error=0.)
def one(a,d,c,dt,i,L):
    mj.mj_step1(a,d)
    assert d.nefc==d.ncon
    bodyid=mj.mj_name2id(a,mj.mjtObj.mjOBJ_GEOM,"body")
    hit=any(k.dist<=0 and bodyid in (k.geom1,k.geom2) for k in d.contact[:d.ncon])
    if hit and L["onset"] is None: L["onset"]=float(d.time)
    for k in d.contact[:d.ncon]: L["pen"]=max(L["pen"],-float(k.dist))
    mj.mj_step2(a,d)
    F=float(d.sensordata[0])
    if not math.isfinite(F) or not np.isfinite(d.qpos).all() or not np.isfinite(d.qvel).all(): raise ValueError("nonfinite")
    L["minforce"]=min(L["minforce"],F)
    L["last"]=F; L["pending"]+=F*dt; L["total"]+=F*dt
    L["J"][0]+=float(d.qfrc_constraint[0]+d.qfrc_constraint[2])*dt
    L["J"][1]+=float(d.qfrc_constraint[1]+d.qfrc_constraint[3])*dt
    p=mass[:2]*(d.qvel[:2]-np.array(c["body_v"]))+mass[2:]*(d.qvel[2:]-np.array(c["counter_v"]))
    L["momentum_error"]=max(L["momentum_error"],float(np.max(np.abs(p-np.array(L["J"])))))
    rec=None
    if (i+1)%round(period/dt)==0:
        ax=0 if c["axis"]=="x" else 1
        ref=m*abs(float(d.qvel[ax]-L["start_v"][ax]))
        rec=dict(tick=(i+1)//round(period/dt),t=float(d.time),instant=L["last"]>0,integral=L["pending"],reference=ref,body_velocity=d.qvel[:2].tolist(),counter_velocity=d.qvel[2:].tolist())
        L["pending"]=0.; L["start_v"]=d.qvel.tolist()
    return rec
def compare(x,y):
    return max(abs(float(a)-float(b)) for a,b in zip(x,y))
def run(c,dt,replay):
    a,d=build(c,dt,True); b,e=build(c,dt,False)
    L=init(d); N=round(duration/dt); out=[]; snap=None; diff=0.
    for i in range(N):
        rec=one(a,d,c,dt,i,L)
        if rec is not None: out.append(rec)
        mj.mj_step1(b,e); mj.mj_step2(b,e)
        diff=max(diff,compare(d.qpos,e.qpos),compare(d.qvel,e.qvel),abs(d.time-e.time),abs(ke(d.qvel)-ke(e.qvel)))
        if replay and snap is None and ((L["pending"]>.01 and c["id"] not in ("no-contact","counter-only")) or (c["id"] in ("no-contact","counter-only") and i==round(period/dt)//2-1)):
            snap=(i+1,state(a,d).tolist(),json.loads(json.dumps(L)),len(out))
    final=dict(qpos=d.qpos.tolist(),qvel=d.qvel.tolist(),K=ke(d.qvel),K0=ke(np.asarray(c["body_v"]+c["counter_v"])),**L)
    replay_error=None; replay_records_match=None
    if replay:
        assert snap is not None
        idx,z,L2,nout=snap; d2=mj.MjData(a); mj.mj_setState(a,d2,np.asarray(z),sig); tail=[]
        for i in range(idx,N):
            t=one(a,d2,c,dt,i,L2)
            if t is not None: tail.append(t)
        replay_error=max(compare(d.qpos,d2.qpos),compare(d.qvel,d2.qvel),abs(L2["total"]-L["total"]),abs(L2["pending"]-L["pending"]))
        replay_records_match=tail==out[nout:]
    ref_total=sum(t["reference"] for t in out); err=max([abs(t["integral"]-t["reference"]) for t in out]+[abs(L["total"]-ref_total)])
    missed=sum(t["reference"]>1e-8 and not t["instant"] for t in out)
    falsepos=sum(t["reference"]<=1e-8 and t["integral"]>0 for t in out)
    missed_integral=sum(t["reference"]>1e-8 and t["integral"]<=0 for t in out)
    return dict(id=c["id"],dt=dt,steps=N,final=final,trace=out,noninterference=diff,reference_error=err,ref_total=ref_total,instant_misses=missed,integral_misses=missed_integral,integral_false_positive=falsepos,replay_error=replay_error,replay_records_match=replay_records_match)
def main():
    t0=time.perf_counter()
    assert importlib.metadata.version("mujoco-core")=="4.0.1" and mj.mj_versionString()=="4.0.1" and np.__version__=="2.3.5"
    runs=[run(c,dt,dt==cfg["dt"][-1]) for c in cfg["cases"] for dt in cfg["dt"]]
    hit=[x for x in runs if x["id"] not in ("no-contact","counter-only")]
    neg=[x for x in runs if x not in hit]; fine=[x for x in runs if x["dt"]==cfg["dt"][-1]]
    c1=all(x["final"]["minforce"]>=-1e-12 and x["final"]["pen"]<=.02 and x["final"]["K"]<=x["final"]["K0"]+.05 for x in runs)
    c2=all(x["reference_error"]<=1e-8 and x["final"]["momentum_error"]<=1e-8 for x in runs)
    c3=all(x["final"]["total"]>.1 and x["integral_misses"]==0 and x["integral_false_positive"]==0 for x in hit) and all(sum(x["instant_misses"] for x in hit if x["dt"]==dt)>=1 for dt in cfg["dt"])
    c4=all(x["final"]["total"]<=1e-10 and all(not t["instant"] and t["integral"]<=1e-10 for t in x["trace"]) for x in neg) and all(abs(M*(x["final"]["qvel"][3]-1))>.1 for x in neg if x["id"]=="counter-only")
    ref={c["id"]:c for c in cfg["cases"]}
    c5=all(x["noninterference"]<=1e-12 for x in runs)
    for x in hit:
        c=ref[x["id"]]; ax=0 if c["axis"]=="x" else 1
        c5=c5 and x["final"]["onset"] is not None and abs(x["final"]["onset"]-c["wall"][ax]/c["body_v"][ax])<=2*x["dt"]+1e-9
    for c in ref:
        a,b=[x for x in runs if x["id"]==c]
        c5=c5 and abs(a["final"]["total"]-b["final"]["total"])<=.03
    c6=all(x["replay_error"]<=1e-12 and x["replay_records_match"] for x in fine)
    elapsed=time.perf_counter()-t0; rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria={f"C{i+1}":bool(v) for i,v in enumerate((c1,c2,c3,c4,c5,c6,elapsed<20 and rss<512))}
    summary=dict(type="summary",criteria=criteria,passed=all(criteria.values()),pairs=len(runs),steps=sum(x["steps"] for x in runs),instant_misses=sum(x["instant_misses"] for x in hit),integral_misses=sum(x["integral_misses"] for x in hit),max_reference_error=max(x["reference_error"] for x in runs),max_momentum_error=max(x["final"]["momentum_error"] for x in runs),max_noninterference=max(x["noninterference"] for x in runs),max_penetration=max(x["final"]["pen"] for x in runs),elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),mujoco=mj.mj_versionString(),numpy=np.__version__,sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("run.py","config.json","requirements.txt")})
    rows=[summary]+[dict(type="dynamic",**x) for x in runs]
    lines=[json.dumps(x,separators=(",",":"),sort_keys=True,allow_nan=False) for x in rows]; raw="\n".join(lines)+"\n"
    (ROOT/"results.jsonl").write_text(raw); print("RESULT_SHA256="+hashlib.sha256(raw.encode()).hexdigest(),flush=True)
    for line in lines: print("RESULT_LINE="+line,flush=True)
    if not summary["passed"]: raise SystemExit(1)
if __name__=="__main__": main()
