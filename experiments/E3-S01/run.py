import hashlib, importlib.metadata, json, math, platform, resource, time
from pathlib import Path
import numpy as np
import mujoco as mj
from controller import choose

ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/"config.json").read_text())
r,cap,q,eta,period=(cfg[k] for k in ("radius","capacity","q","eta","control_dt"))
sig=mj.mjtState.mjSTATE_INTEGRATION
axes=[np.array(d,dtype=float) for d in ((1,0,0),(0,1,0),(-1,0,0),(0,-1,0))]
keys=("rays","touch","fuel_kg")

def build(c,dt):
    sr=" ".join(map(str,cfg["contact"]["solref"]))
    si=" ".join(map(str,cfg["contact"]["solimp"]))
    boxes="".join(f'<geom name="{o["name"]}" type="box" pos="{o["pos"][0]} {o["pos"][1]} 0" size="{o["half"][0]} {o["half"][1]} .5"/>' for o in c["boxes"])
    def body(name,pos,mass,site):
        return f'<body name="{name}" pos="{pos[0]} {pos[1]} 0"><joint type="slide" axis="1 0 0" limited="false" damping="0" frictionloss="0" armature="0"/><joint type="slide" axis="0 1 0" limited="false" damping="0" frictionloss="0" armature="0"/><geom name="{name}" type="sphere" size="{r}" mass="{mass}"/><site name="{site}" pos="0 0 0" size=".005"/></body>'
    xml=f"""<mujoco model="E3-S01">
      <option timestep="{dt}" gravity="0 0 0" integrator="Euler" solver="Newton" iterations="100" tolerance="1e-12"/>
      <default><geom condim="1" margin="0" gap="0" solref="{sr}" solimp="{si}"/></default>
      <worldbody>{boxes}{body("body",c["body"],c["m"],"a")}{body("counter",c["counter"],c["M"],"b")}</worldbody>
      <tendon><spatial name="link" limited="false" stiffness="0" damping="0"><site site="a"/><site site="b"/></spatial></tendon>
      <actuator><motor name="pull" tendon="link" gear="-1" ctrllimited="true" ctrlrange="0 1"/></actuator>
    </mujoco>"""
    m=mj.MjModel.from_xml_string(xml)
    assert m.nq==m.nv==4 and m.nu==1
    assert abs(m.body_mass[1]-c["m"])<=1e-12 and abs(m.body_mass[2]-c["M"])<=1e-12
    d=mj.MjData(m)
    d.qvel[:]=c["v"]; mj.mj_forward(m,d)
    ids={name:mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM,name) for name in ("body","counter","dock")}
    return m,d,ids

def locations(c,d):
    return np.asarray(c["body"])+d.qpos[:2], np.asarray(c["counter"])+d.qpos[2:]

def touching(d,ids):
    return any(k.dist<=0 and ids["body"] in (k.geom1,k.geom2) for k in d.contact[:d.ncon])

def observe(m,d,ids,L,c):
    p,_=locations(c,d); p3=np.array([p[0],p[1],0.])
    hit=[]
    for v in axes:
        z=float(mj.mj_ray(m,d,p3,v,None,True,1,None,None))
        dist=max(0.,z-r)
        hit.append(None if z<0 or dist>cfg["range"] else dist)
    obs={"rays":hit,"touch":bool(touching(d,ids)),"fuel_kg":float(L["R"])}
    return json.loads(json.dumps(obs,allow_nan=False))

def program(c):
    return {k:c[k] for k in ("pull","pull_ticks","exchange")}

def ledger(c):
    return dict(R=c["R"],S=cap-c["R"],X=c["X"],Z=0.,W=0.,Wbody=0.,Wcounter=0.,Q=0.,C=0.,
                Jx=0.,Jy=0.,accepted=0.,transfers=0,swap_motion_err=0.,mass_err=0.,energy_err=0.,
                work_err=0.,momentum_err=0.,force_err=0.,force_sum_err=0.,max_pen=0.,
                bad_active=0,touch_steps=0,onset=None,min_sep=1e30,min_stock=1e30,min_work=0.)

def exchange(d,ids,L,c,request):
    if request<=0 or np.max(np.abs(d.qvel[:2]))>1e-12 or ids["dock"]<0:
        return 0.
    p,_=locations(c,d)
    ok=any(k.dist<=0 and set((k.geom1,k.geom2))==set((ids["body"],ids["dock"])) and
           k.pos[0]-p[0]<=-.24 and abs(k.pos[1]-p[1])<=.025 for k in d.contact[:d.ncon])
    if not ok: return 0.
    before=np.concatenate((d.qpos.copy(),d.qvel.copy()))
    u=min(request,L["X"],L["S"])
    if u>0:
        L["R"]+=u; L["S"]-=u; L["X"]-=u; L["Z"]+=u
        L["accepted"]+=u; L["transfers"]+=1
    L["swap_motion_err"]=max(L["swap_motion_err"],float(np.max(np.abs(before-np.concatenate((d.qpos,d.qvel))))))
    return u

def segment_box(p,b,o):
    lo,hi=0.,1.
    for i in range(2):
        a=float(p[i]); v=float(b[i]-p[i]); x=o["pos"][i]; h=o["half"][i]
        if abs(v)<1e-15:
            if a<x-h or a>x+h: return False
        else:
            t1,t2=sorted(((x-h-a)/v,(x+h-a)/v))
            lo=max(lo,t1); hi=min(hi,t2)
            if lo>hi: return False
    return True

def penetration(p,b,boxes):
    sep=math.hypot(*(b-p)); pen=max(0.,2*r-sep)
    for o in boxes:
        for a in (p,b):
            dx=abs(float(a[0])-o["pos"][0])-o["half"][0]
            dy=abs(float(a[1])-o["pos"][1])-o["half"][1]
            dist=math.hypot(max(0.,dx),max(0.,dy))+min(0.,max(dx,dy))
            pen=max(pen,r-dist)
    return sep,pen

def kinetic(v,c):
    return .5*(c["m"]*float(np.dot(v[:2],v[:2]))+c["M"]*float(np.dot(v[2:],v[2:])))

def state(m,d):
    a=np.empty(mj.mj_stateSize(m,sig),dtype=np.float64)
    mj.mj_getState(m,d,a,sig); return a

def advance(m,d,ids,L,c,dt,i,cmd,record):
    mj.mj_step1(m,d)
    assert d.nefc==d.ncon
    p,b=locations(c,d); delta=b-p; dist=math.hypot(*delta)
    assert dist>0
    n=delta/dist
    qpre=d.qpos.copy(); v=d.qvel.copy()
    if touching(d,ids):
        L["touch_steps"]+=1
        if L["onset"] is None: L["onset"]=float(d.time)
    trace=None
    nstep=round(period/dt)
    if i%nstep==0:
        obs=observe(m,d,ids,L,c)
        tick=i//nstep
        cmd=choose(obs,tick,program(c),c["controller"])
        if record: trace={"tick":tick,"obs":obs,"cmd":cmd.copy(),"start_pos":p.tolist(),"start_v":v.tolist(),"W0":L["W"]}
        u=exchange(d,ids,L,c,cmd["exchange"])
        if record: trace["accepted"]=u
    F=cmd["pull"]; closing=float(np.dot(v[:2]-v[2:],n)); U=eta*q*L["R"]; inv=1/c["m"]+1/c["M"]
    if F>0:
        if U<=1e-12 or dist<=2*r or closing<-1e-12 or d.ncon or any(segment_box(p,b,o) for o in c["boxes"]):
            F=0.
        else:
            a=max(0.,closing)*dt
            F=min(F,2*U/(a+math.sqrt(a*a+4*inv*dt*dt*U)))
    if F:
        L["bad_active"]+=int(bool(d.ncon) or any(segment_box(p,b,o) for o in c["boxes"]))
    d.ctrl[0]=F
    ncon=int(d.ncon)
    mj.mj_step2(m,d)
    dq=d.qpos-qpre; vn=d.qvel
    fa=d.qfrc_actuator; fc=d.qfrc_constraint
    L["force_err"]=max(L["force_err"],float(np.max(np.abs(fa-np.concatenate((F*n,-F*n))))))
    L["force_sum_err"]=max(L["force_sum_err"],float(np.max(np.abs(fa[:2]+fa[2:]))))
    w1=float(np.dot(fa[:2],dq[:2])); w2=float(np.dot(fa[2:],dq[2:])); w=w1+w2
    L["W"]+=w; L["Wbody"]+=w1; L["Wcounter"]+=w2; L["Q"]+=(1/eta-1)*w
    L["R"]-=w/(eta*q); L["S"]+=w/(eta*q); L["C"]+=float(np.dot(fc,dq))
    L["Jx"]+=float(fc[0]+fc[2])*dt; L["Jy"]+=float(fc[1]+fc[3])*dt
    p,b=locations(c,d); sep,pen=penetration(p,b,c["boxes"])
    L["min_sep"]=min(L["min_sep"],sep); L["max_pen"]=max(L["max_pen"],pen)
    L["min_stock"]=min(L["min_stock"],L["R"],L["S"],L["X"],L["Z"]); L["min_work"]=min(L["min_work"],w)
    K=kinetic(vn,c); K0=kinetic(np.asarray(c["v"]),c)
    L["mass_err"]=max(L["mass_err"],abs(L["R"]+L["S"]-cap),abs(L["X"]+L["Z"]-c["X"]),abs(L["R"]+L["S"]+L["X"]+L["Z"]-cap-c["X"]))
    L["energy_err"]=max(L["energy_err"],abs(q*(L["R"]+L["X"])+K+L["Q"]-L["C"]-q*(c["R"]+c["X"])-K0))
    L["work_err"]=max(L["work_err"],abs(K-K0-L["W"]-L["C"]))
    p0=c["m"]*np.asarray(c["v"][:2])+c["M"]*np.asarray(c["v"][2:])
    P=c["m"]*vn[:2]+c["M"]*vn[2:]
    L["momentum_err"]=max(L["momentum_err"],float(np.max(np.abs(P-p0-np.array([L["Jx"],L["Jy"]])))))
    if not np.isfinite(d.qpos).all() or not np.isfinite(vn).all() or not all(math.isfinite(x) for x in L.values() if x is not None): raise ValueError("nonfinite")
    return cmd,trace,ncon

def checkpoint(c,d,L):
    p,b=locations(c,d)
    return dict(body=p.tolist(),counter=b.tolist(),v=d.qvel.tolist(),K=kinetic(d.qvel,c),**L)

def reference(c):
    F=c["pull"] if c["controller"]=="script" else 0.
    inv=1/c["m"]+1/c["M"]
    T=min(len(c["pull_ticks"])*period,math.sqrt(2*eta*q*c["R"]/(F*F*inv))) if F else 0.
    n=np.asarray(c["counter"])-np.asarray(c["body"]); n=n/np.linalg.norm(n)
    f=F*T*(c["duration"]-.5*T)
    return dict(body=(np.asarray(c["body"])+n*f/c["m"]).tolist(),
                counter=(np.asarray(c["counter"])-n*f/c["M"]).tolist(),
                v=np.concatenate((n*F*T/c["m"],-n*F*T/c["M"])).tolist(),
                W=.5*F*F*inv*T*T,R=c["R"]-(.5*F*F*inv*T*T)/(eta*q))

def run(c,dt,replay):
    m,d,ids=build(c,dt); L=ledger(c); N=round(c["duration"]/dt); nstep=round(period/dt)
    cmd={"pull":0.,"exchange":0.}; traces=[]; snap=None
    for i in range(N):
        cmd,t,ncon=advance(m,d,ids,L,c,dt,i,cmd,True)
        if t is not None: traces.append(t)
        if (i+1)%nstep==0:
            cp=checkpoint(c,d,L)
            traces[-1].update(end_pos=cp["body"],end_v=cp["v"],R=cp["R"],work=cp["W"]-traces[-1]["W0"])
        if replay and snap is None and ((c["id"]=="collision" and ncon>0) or (c["id"]!="collision" and i==N//2-1)):
            snap=(i+1,state(m,d).tolist(),json.loads(json.dumps(L)),cmd.copy())
    final=checkpoint(c,d,L); err=None; replay_contact=None
    if replay:
        assert snap is not None and snap[0]<N
        i,z,L2,cmd2=snap; d2=mj.MjData(m); mj.mj_setState(m,d2,np.asarray(z),sig)
        for j in range(i,N):
            cmd2,_,nc=advance(m,d2,ids,L2,c,dt,j,cmd2,False)
            if j==i: replay_contact=bool(nc)
        err=max(float(np.max(np.abs(state(m,d)-state(m,d2)))),
                max(abs(L[k]-L2[k]) if L[k] is not None and L2[k] is not None else float(L[k]!=L2[k]) for k in L),
                float(cmd!=cmd2))
    referr=None
    if not c["boxes"]:
        ref=reference(c)
        referr={"x":max(max(abs(a-b) for a,b in zip(final[k],ref[k])) for k in ("body","counter")),
                "v":max(abs(a-b) for a,b in zip(final["v"],ref["v"])),
                "W":abs(final["W"]-ref["W"]),"R":abs(final["R"]-ref["R"])}
    return dict(id=c["id"],dt=dt,steps=N,final=final,trace=traces,replay_error=err,replay_contact=replay_contact,reference_error=referr)

def sensor_case(s):
    shift=s.get("shift",[0,0])
    boxes=[dict(o,pos=[o["pos"][i]+shift[i] for i in range(2)]) for o in s["boxes"]]
    c=dict(body=shift,counter=[shift[0]-2,shift[1]],m=2,M=3,v=[0,0,0,0],R=.5,X=s.get("X",0),boxes=boxes)
    m,d,ids=build(c,cfg["steps"][-1]); obs=observe(m,d,ids,ledger(c),c)
    cmd=choose(obs,0,{"pull":0.,"pull_ticks":[],"exchange":.1},"script")
    return dict(id=s["id"],obs=obs,cmd=cmd)

def same(a,b):
    return a["touch"]==b["touch"] and abs(a["fuel_kg"]-b["fuel_kg"])<=1e-12 and all((x is None and y is None) or (x is not None and y is not None and abs(x-y)<=1e-8) for x,y in zip(a["rays"],b["rays"]))

def main():
    start=time.perf_counter()
    assert importlib.metadata.version("mujoco-core")=="4.0.1" and mj.mj_versionString()=="4.0.1" and np.__version__=="2.3.5"
    runs=[run(c,dt,dt==cfg["steps"][-1]) for c in cfg["cases"] for dt in cfg["steps"]]
    sensors=[sensor_case(s) for s in cfg["sensors"]]
    fine={x["id"]:x for x in runs if x["dt"]==cfg["steps"][-1]}
    coarse={x["id"]:x for x in runs if x["dt"]==cfg["steps"][0]}
    f={k:x["final"] for k,x in fine.items()}
    maxall=lambda k:max(x["final"][k] for x in runs)
    maxfine=lambda k:max(x[k] for x in f.values())
    minall=lambda k:min(x["final"][k] for x in runs)
    fine_refs=[x["reference_error"] for x in fine.values() if x["reference_error"] is not None]
    maxref={k:max(x[k] for x in fine_refs) for k in ("x","v","W","R")}
    def refmax(rs): return max(max(x["reference_error"][k] for k in ("x","v","W")) for name,x in rs.items() if name in ("x","y","heavy","limited","reserved"))
    cf,cc=refmax(fine),refmax(coarse)
    C1=(maxall("mass_err")<=1e-9 and minall("min_stock")>=-1e-9 and minall("min_work")>=-1e-10 and maxall("force_err")<=1e-9 and maxall("force_sum_err")<=1e-9 and maxall("bad_active")==0)
    C2=maxall("momentum_err")<=1e-8 and max(maxfine("energy_err"),maxfine("work_err"))<=.05 and max(maxall("energy_err"),maxall("work_err"))<=.20 and cf<=.65*cc+1e-9
    C3=all(maxref[k]<=v for k,v in dict(x=.005,v=.005,W=.005,R=.001).items()) and f["heavy"]["body"][0]<f["x"]["body"][0] and f["y"]["body"][1]>.1 and all(v>.01 for v in f["reserved"]["body"]) and all(abs(f[k]["W"])<=1e-9 and max(abs(v) for v in f[k]["v"])<=1e-9 for k in ("empty","idle")) and all(abs(f[k]["W"]-w)<=1e-9 and max(abs(v) for v in f[k]["v"])>0 for k,w in (("limited",.1),("reserved",.075))) and f["x"]["Wbody"]>0 and f["x"]["Wcounter"]>0
    col=f["collision"]
    C4=maxall("max_pen")<=.02 and all(x["final"]["touch_steps"]==0 for x in runs if x["id"] in ("x","y","heavy","empty","limited","idle","reserved")) and all(x["final"]["touch_steps"]>0 and x["final"]["K"]<=1.05 and x["final"]["C"]<=.05 and abs(x["final"]["W"])<=1e-9 and abs(x["final"]["Jy"])>.1 for x in runs if x["id"]=="collision") and col["onset"] is not None and abs(col["onset"]-.5)<=.002
    sd={x["id"]:x for x in sensors}; exp={"clear":.75,"occluded-a":.35,"occluded-b":.35,"far":None,"absent":None,"translated":.75,"hidden-stock":.35}
    C5=all(same(x["obs"],dict(rays=[exp[x["id"]],None,None,None],touch=False,fuel_kg=.5)) and set(x["obs"])==set(keys) for x in sensors) and all(same(sd[a]["obs"],sd[b]["obs"]) and sd[a]["cmd"]==sd[b]["cmd"] for a,b in (("occluded-a","occluded-b"),("occluded-a","hidden-stock"),("far","absent"),("translated","clear"))) and f["idle"]["W"]==0
    def refill_check(x):
        z=x["final"]; name=x["id"]
        if name=="refill":
            return abs(z["accepted"]-.08)<=1e-9 and z["transfers"]==1 and abs(z["X"])<=1e-9 and abs(z["Z"]-.08)<=1e-9 and .05<z["W"]<=.4+1e-9 and z["touch_steps"]>0
        if name in ("remote","dry-dock","closed","no-residue"):
            return abs(z["accepted"])<=1e-9 and z["transfers"]==0 and abs(z["W"])<=1e-9 and (z["touch_steps"]==0 if name=="remote" else z["touch_steps"]>0)
        return True
    C6=all(refill_check(x) for x in runs)
    C7=all(x["replay_error"]<=1e-12 and (x["id"]!="collision" or x["replay_contact"]) for x in fine.values()) and all(len(x["trace"])==round(x["steps"]*x["dt"]/period) and all("end_pos" in t and "work" in t and set(t["obs"])==set(keys) for t in x["trace"]) for x in runs)
    C8=([t["cmd"] for t in fine["refill"]["trace"]]==[t["cmd"] for t in fine["remote"]["trace"]]) and fine["remote"]["trace"][0]["obs"]["rays"][2] is not None and not fine["remote"]["trace"][0]["obs"]["touch"] and fine["refill"]["trace"][0]["obs"]["touch"] and maxall("swap_motion_err")==0 and minall("min_sep")>=2*r-.02 and C6
    elapsed=time.perf_counter()-start; rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria={k:bool(v) for k,v in zip(("C1","C2","C3","C4","C5","C6","C7","C8","C9"),(C1,C2,C3,C4,C5,C6,C7,C8,elapsed<45 and rss<512))}
    summary=dict(criteria=criteria,passed=all(criteria.values()),runs=len(runs),steps=sum(x["steps"] for x in runs),sensor_cases=len(sensors),reference_fine=maxref,free_refinement=[cc,cf],max_energy_fine=max(maxfine("energy_err"),maxfine("work_err")),max_energy_all=max(maxall("energy_err"),maxall("work_err")),max_momentum=maxall("momentum_err"),max_mass=maxall("mass_err"),max_force_error=maxall("force_err"),max_force_sum_error=maxall("force_sum_err"),max_penetration=maxall("max_pen"),elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),mujoco=mj.mj_versionString(),numpy=np.__version__,sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("run.py","controller.py","config.json","requirements.txt")})
    records=[dict(type="summary",**summary)]+[dict(type="dynamic",**x) for x in runs]+[dict(type="sensor",**x) for x in sensors]
    lines=[json.dumps(x,separators=(",",":"),sort_keys=True,allow_nan=False) for x in records]
    raw="\n".join(lines)+"\n"; (ROOT/"results.jsonl").write_text(raw)
    print("RESULT_SHA256="+hashlib.sha256(raw.encode()).hexdigest(),flush=True)
    for l in lines: print("RESULT_LINE="+l,flush=True)
    if not summary["passed"]: raise SystemExit(1)

if __name__=="__main__": main()
