import hashlib, importlib.metadata, json, math, platform, resource, time
from pathlib import Path
import numpy as np
import mujoco as mj
from controller import choose
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/"config.json").read_text())
r,cap,q,eta,basal,period=(cfg[k] for k in ("radius","capacity","q","eta","basal","period"))
sig=mj.mjtState.mjSTATE_INTEGRATION
axes=[np.array(v,dtype=float) for v in ((1,0,0),(0,1,0),(-1,0,0),(0,-1,0))]
keys={"rays","touch","touch_impulse_Ns","fuel_kg","velocity_body"}
def build(c,dt):
    wall=""
    if c["wall"]:
        w=c["wall"]; wall=f'<geom name="{w["name"]}" type="box" pos="{w["face"]+.1} 0 0" size=".1 .6 .5"/>'
    xml=f'<mujoco><option timestep="{dt}" gravity="0 0 0" integrator="Euler" solver="Newton" iterations="100" tolerance="1e-12"/><default><geom condim="1" margin="0" gap="0" solref="{cfg["solref"]}" solimp="{cfg["solimp"]}"/></default><worldbody>{wall}<body name="body"><joint type="slide" axis="1 0 0" damping="0" armature="0" frictionloss="0"/><joint type="slide" axis="0 1 0" damping="0" armature="0" frictionloss="0"/><geom name="body" type="sphere" size="{r}" mass="{c["m"]}"/></body></worldbody></mujoco>'
    m=mj.MjModel.from_xml_string(xml); d=mj.MjData(m); mj.mj_forward(m,d)
    assert m.nq==m.nv==2 and abs(m.body_mass[1]-c["m"])<=1e-12
    ids={name:mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM,name) for name in ("body","dock")}
    return m,d,ids
def init(c):
    return dict(R=c["R"],S=cap-c["R"],X=c["X"],Z=0.,Q=0.,D=0.,A=0.,Wplus=0.,Wsigned=0.,Wbody=0.,C=0.,B=0.,Mmiss=0.,Jsub=[0.,0.],Jwall=[0.,0.],Jenv_sub=[0.,0.],Jenv_wall=[0.,0.],pending=0.,prev_Jwall=0.,impulse_err=0.,accepted=0.,transfers=0,swap_err=0.,mass_err=0.,energy_err=0.,mechanical_err=0.,identity_err=0.,momentum_err=0.,reaction_err=0.,force_err=0.,minstock=0.,minpositive=0.,max_u=0.,max_pen=0.,max_speed=0.,max_force=0.,max_active_force=0.,onset=None,touch_steps=0,stall_steps=0,stall_work=0.,stall_D=0.,wall_no_contact_impulse=0.,initial_touch=False,empty_onset=None,empty_speed=None,empty_active_steps=0,traces=[],current=None,cmd={"u":[0.,0.],"exchange":False})
def state(m,d):
    a=np.empty(mj.mj_stateSize(m,sig)); mj.mj_getState(m,d,a,sig); return a
def touch_contacts(d,ids):
    return [k for k in d.contact[:d.ncon] if k.dist<=0 and ids["body"] in (k.geom1,k.geom2)]
def observe(m,d,ids,L,hit):
    x,y=d.qpos; p=np.array([x,y,0.]); rays=[]
    for a in axes:
        z=float(mj.mj_ray(m,d,p,a,None,True,1,None,None))
        dist=max(0.,z-r)
        rays.append(None if z<0 or dist>cfg["range"] else dist)
    obs={"rays":rays,"touch":bool(hit),"touch_impulse_Ns":float(L["pending"]),"fuel_kg":float(L["R"]),"velocity_body":d.qvel.tolist()}
    assert set(obs)==keys
    return json.loads(json.dumps(obs,allow_nan=False))
def exchange(d,ids,L,hit):
    if ids["dock"]<0 or math.hypot(*d.qvel)>cfg["dock_speed"]: return 0.
    ok=any(ids["dock"] in (k.geom1,k.geom2) and k.pos[0]-d.qpos[0]>=.24 and abs(k.pos[1]-d.qpos[1])<=.025 for k in hit)
    if not ok: return 0.
    before=np.r_[d.qpos.copy(),d.qvel.copy()]
    u=min(cfg["exchange_limit"],L["X"],L["S"])
    if u>0:
        L["R"]+=u; L["S"]-=u; L["X"]-=u; L["Z"]+=u
        L["accepted"]+=u; L["transfers"]+=1
    L["swap_err"]=max(L["swap_err"],float(np.max(np.abs(np.r_[d.qpos,d.qvel]-before))))
    return u
def command_program(c):
    return {k:c[k] for k in ("u","drive_until","retreat_at","exchange_at","controller")}
def subtract_fuel(L,e):
    dm=e/q
    L["R"]-=dm; L["S"]+=dm
def one(m,d,ids,L,c,dt,i,program):
    mj.mj_step1(m,d); assert d.nefc==d.ncon
    hit=touch_contacts(d,ids)
    if hit:
        L["touch_steps"]+=1
        if L["onset"] is None: L["onset"]=float(d.time)
        L["max_pen"]=max(L["max_pen"],max(-float(k.dist) for k in hit))
    n=round(period/dt); tick=i//n
    if i%n==0:
        if i==0: L["initial_touch"]=bool(hit)
        obs=observe(m,d,ids,L,hit)
        L["impulse_err"]=max(L["impulse_err"],abs(L["pending"]-abs(L["Jwall"][0]-L["prev_Jwall"])))
        L["pending"]=0.; L["prev_Jwall"]=L["Jwall"][0]
        cmd=choose(obs,tick,program,period); L["cmd"]=cmd
        u=exchange(d,ids,L,hit) if cmd["exchange"] else 0.
        L["current"]={"tick":tick,"obs":obs,"cmd":cmd,"accepted":u,"start_pos":d.qpos.tolist(),"start_v":d.qvel.tolist(),"R_after_exchange":L["R"],"W0":L["Wplus"],"D0":L["D"],"B0":L["B"]}
    v=d.qvel.copy(); vx,vy=map(float,v); sp=math.hypot(vx,vy); g=c["gamma"]; mass=c["m"]
    eb=min(max(0.,q*L["R"]),basal*dt); subtract_fuel(L,eb); L["B"]+=eb; L["Q"]+=eb; L["Mmiss"]+=basal*dt-eb
    ux,uy=L["cmd"]["u"]; U=eta*q*L["R"]
    if U<=1e-12:
        ux=uy=0.
        if L["empty_onset"] is None: L["empty_onset"]=float(d.time); L["empty_speed"]=sp
    norm2=ux*ux+uy*uy; dot=ux*vx+uy*vy
    if g>0 and norm2>0 and g*(norm2-dot)*dt>U:
        C=U/(g*dt); root=math.sqrt(dot*dot+4*norm2*C)
        alpha=(dot+root)/(2*norm2) if dot>=0 else 2*C/(root-dot)
        assert 0<=alpha<=1+1e-12
        ux*=alpha; uy*=alpha
    fx=g*(ux-vx); fy=g*(uy-vy); ws=(fx*ux+fy*uy)*dt; wb=(fx*vx+fy*vy)*dt; dis=g*((ux-vx)**2+(uy-vy)**2)*dt
    wp=max(0.,ws); absorb=max(0.,-ws)
    subtract_fuel(L,wp/eta); L["Q"]+=wp*(1/eta-1)+absorb; L["A"]+=absorb; L["D"]+=dis
    L["Wplus"]+=wp; L["Wsigned"]+=ws; L["Wbody"]+=wb
    L["minstock"]=min(L["minstock"],L["R"],L["S"],L["X"],L["Z"])
    L["minpositive"]=min(L["minpositive"],wp,dis,absorb,eb)
    L["max_u"]=max(L["max_u"],math.hypot(ux,uy)); L["max_force"]=max(L["max_force"],math.hypot(fx,fy))
    if ux or uy: L["max_active_force"]=max(L["max_active_force"],math.hypot(fx,fy))
    if U<=1e-12 and (ux or uy): L["empty_active_steps"]+=1
    if hit and sp<=cfg["dock_speed"] and wp>0 and dis>0:
        L["stall_steps"]+=1; L["stall_work"]+=wp; L["stall_D"]+=dis
    d.qfrc_applied[:]=[fx,fy]; mj.mj_step2(m,d)
    wx,wy=map(float,d.qfrc_constraint)
    L["force_err"]=max(L["force_err"],abs(float(d.qfrc_applied[0])-g*(ux-vx)),abs(float(d.qfrc_applied[1])-g*(uy-vy)))
    L["Jsub"][0]+=fx*dt; L["Jsub"][1]+=fy*dt; L["Jenv_sub"][0]-=fx*dt; L["Jenv_sub"][1]-=fy*dt
    L["Jwall"][0]+=wx*dt; L["Jwall"][1]+=wy*dt; L["Jenv_wall"][0]-=wx*dt; L["Jenv_wall"][1]-=wy*dt
    L["pending"]+=abs(wx)*dt
    if not hit: L["wall_no_contact_impulse"]+=math.hypot(wx,wy)*dt
    L["C"]+=(wx*vx+wy*vy)*dt
    nx,ny=map(float,d.qvel); K=.5*mass*(nx*nx+ny*ny)
    L["max_speed"]=max(L["max_speed"],math.hypot(nx,ny))
    L["reaction_err"]=max(L["reaction_err"],*(abs(a+b) for a,b in zip(L["Jsub"],L["Jenv_sub"])),*(abs(a+b) for a,b in zip(L["Jwall"],L["Jenv_wall"])))
    L["momentum_err"]=max(L["momentum_err"],abs(mass*nx-L["Jsub"][0]-L["Jwall"][0]),abs(mass*ny-L["Jsub"][1]-L["Jwall"][1]))
    L["identity_err"]=max(L["identity_err"],abs(L["Wsigned"]-L["Wbody"]-L["D"]))
    L["mass_err"]=max(L["mass_err"],abs(L["R"]+L["S"]-cap),abs(L["X"]+L["Z"]-c["X"]),abs(L["R"]+L["S"]+L["X"]+L["Z"]-cap-c["X"]))
    L["energy_err"]=max(L["energy_err"],abs(q*(L["R"]+L["X"])+K+L["Q"]+L["D"]-L["C"]-q*(c["R"]+c["X"])))
    L["mechanical_err"]=max(L["mechanical_err"],abs(K-L["Wbody"]-L["C"]))
    if not all(math.isfinite(a) for a in (nx,ny,*d.qpos,L["R"],L["Q"],L["energy_err"],L["momentum_err"],L["identity_err"])): raise ValueError("nonfinite")
    if (i+1)%n==0:
        L["current"].update(end_pos=d.qpos.tolist(),end_v=d.qvel.tolist(),R=L["R"],Wplus=L["Wplus"]-L["current"]["W0"],D=L["D"]-L["current"]["D0"],B=L["B"]-L["current"]["B0"])
        L["traces"].append(L["current"]); L["current"]=None
    return bool(hit)
def reference(c):
    k=c["gamma"]/c["m"]; T=c["drive_until"]; L=c["duration"]
    u=np.array(c["u"]); z=math.exp(-k*T); v=u*(1-z); x=u*(T-(1-z)/k)+v*(1-math.exp(-k*(L-T)))/k; v=v*math.exp(-k*(L-T))
    W=c["m"]*float(np.dot(u,u))*(1-z)
    return dict(x=x.tolist(),v=v.tolist(),W=W,R=c["R"]-(basal*L+W/eta)/q)
def run(c,dt,replay):
    m,d,ids=build(c,dt); L=init(c); p=command_program(c); N=round(c["duration"]/dt); snap=None
    for i in range(N):
        hit=one(m,d,ids,L,c,dt,i,p)
        if replay and snap is None and ((c["id"] in ("dock","barrier","dry") and hit) or (c["id"] not in ("dock","barrier","dry") and i==N//2-1)):
            snap=(i+1,state(m,d).tolist(),json.loads(json.dumps(L)))
    L["impulse_err"]=max(L["impulse_err"],abs(L["pending"]-abs(L["Jwall"][0]-L["prev_Jwall"])))
    final=dict(x=d.qpos.tolist(),v=d.qvel.tolist(),K=.5*c["m"]*float(np.dot(d.qvel,d.qvel)),**L)
    referr=None
    if c["id"] in ("x","y","heavy","reserved"):
        ref=reference(c)
        referr={"x":max(abs(a-b) for a,b in zip(final["x"],ref["x"])),"v":max(abs(a-b) for a,b in zip(final["v"],ref["v"])),"W":abs(L["Wplus"]-ref["W"]),"R":abs(L["R"]-ref["R"])}
    replay_err=None; replay_trace=None
    if replay:
        assert snap is not None and snap[0]<N
        idx,z,L2=snap; e=mj.MjData(m); mj.mj_setState(m,e,np.asarray(z),sig)
        for i in range(idx,N): one(m,e,ids,L2,c,dt,i,p)
        L2["impulse_err"]=max(L2["impulse_err"],abs(L2["pending"]-abs(L2["Jwall"][0]-L2["prev_Jwall"])))
        # Exact equality for full ledger/traces; state numeric tolerance separately.
        replay_err=float(np.max(np.abs(state(m,d)-state(m,e))))
        replay_trace=(L==L2)
    return dict(type="dynamic",id=c["id"],dt=dt,steps=N,final=final,reference_error=referr,replay_error=replay_err,replay_exact_ledger=replay_trace)
def main():
    t0=time.perf_counter()
    assert importlib.metadata.version("mujoco-core")=="4.0.1" and mj.mj_versionString()=="4.0.1" and np.__version__=="2.3.5"
    rs=[run(c,dt,dt==cfg["dt"][-1]) for c in cfg["cases"] for dt in cfg["dt"]]
    fine={x["id"]:x for x in rs if x["dt"]==cfg["dt"][-1]}; f={k:x["final"] for k,x in fine.items()}
    ff=[x["final"] for x in rs]; maxall=lambda k:max(x[k] for x in ff); maxfine=lambda k:max(x[k] for x in f.values())
    free=("x","y","heavy","reserved")
    maxref={k:max(fine[a]["reference_error"][k] for a in free) for k in ("x","v","W","R")}
    er=[max(max(x["reference_error"][k] for k in ("x","v","W")) for x in rs if x["dt"]==dt and x["id"] in free) for dt in cfg["dt"]]
    C1=min(x["minstock"] for x in ff)>=-1e-9 and min(x["minpositive"] for x in ff)>=-1e-10 and maxall("mass_err")<=1e-9 and maxall("max_u")<=.5+1e-12
    C2=maxall("momentum_err")<=1e-8 and maxall("reaction_err")<=1e-8 and maxall("force_err")<=1e-9 and maxall("wall_no_contact_impulse")<=1e-8 and maxall("identity_err")<=1e-8 and max(maxfine("energy_err"),maxfine("mechanical_err"))<=.05 and max(maxall("energy_err"),maxall("mechanical_err"))<=.20 and er[1]<=.65*er[0]+1e-9
    C3=all(maxref[k]<=v for k,v in dict(x=.003,v=.003,W=.003,R=.001).items()) and all(max(abs(z) for z in f[k]["x"]+f[k]["v"])<=1e-9 and f[k]["Wplus"]<=1e-9 for k in ("idle","no-grip","empty")) and f["heavy"]["x"][0]<f["x"]["x"][0] and min(f["reserved"]["x"])>0 and 0<f["limited"]["Wplus"]<=eta*q*.008+1e-9 and f["limited"]["R"]<=1e-9 and f["limited"]["empty_speed"] is not None and math.hypot(*f["limited"]["v"])<f["limited"]["empty_speed"] and all(abs(f[k]["B"]-.04)<=1e-9 for k in ("idle","no-grip")) and abs(f["empty"]["Mmiss"]-.04)<=1e-9
    C4=maxall("max_pen")<=.02 and maxall("impulse_err")<=1e-8 and all(not x["final"]["initial_touch"] for x in rs) and all(x["final"]["onset"] is not None and x["final"]["onset"]<2.5 and abs(x["final"]["Jwall"][0])>.1 for x in rs if x["id"] in ("dock","barrier","dry")) and all(x["final"]["touch_steps"]==0 for x in rs if x["id"]=="remote" or x["id"] in free+("idle","no-grip","empty","limited"))
    def docking(x):
        z=x["final"]; id=x["id"]
        if id=="dock":
            tr=[t for t in z["traces"] if t["accepted"]>0]
            return abs(z["accepted"]-.08)<=1e-9 and z["transfers"]==1 and abs(z["X"])<=1e-9 and abs(z["Z"]-.08)<=1e-9 and len(tr)==1 and tr[0]["tick"] in (10,11) and tr[0]["obs"]["touch"] and math.hypot(*tr[0]["start_v"])<=.01 and tr[0]["start_pos"][0]>=.38 and tr[0]["start_pos"][0]-z["x"][0]>=.2
        if id in ("remote","barrier","dry"):
            return z["accepted"]==0 and z["transfers"]==0
        return True
    C5=all(docking(x) for x in rs) and all(x["swap_err"]==0 for x in ff)
    for dt in cfg["dt"]:
        rr={x["id"]:x["final"] for x in rs if x["dt"]==dt}
        C5=C5 and rr["dock"]["R"]-rr["dry"]["R"]>=.07 and all([t["cmd"] for t in rr["dock"]["traces"]]==[t["cmd"] for t in rr[a]["traces"]] for a in ("remote","barrier","dry")) and any(t["tick"] in (10,11) and t["obs"]["rays"][0] is not None and not t["obs"]["touch"] and t["accepted"]==0 for t in rr["remote"]["traces"])
    C6=all(x["final"]["stall_steps"]>0 and x["final"]["stall_work"]>0 and x["final"]["stall_D"]>0 for x in rs if x["id"] in ("dock","barrier","dry")) and all(x["final"]["max_force"]==0 for x in rs if x["id"]=="no-grip") and maxall("empty_active_steps")==0
    C7=all(all(set(t["obs"])==keys and t["obs"]["velocity_body"]==t["start_v"] and -1e-9<=t["obs"]["fuel_kg"]<=cap+1e-9 for t in x["traces"]) for x in ff) and all(abs(x["final"]["traces"][0]["obs"]["rays"][0]-.4)<=1e-8 for x in rs if x["id"]=="dock") and all(x["final"]["traces"][0]["obs"]["rays"][0] is None for x in rs if x["id"]=="remote")
    C8=all(x["replay_error"]<=1e-12 and x["replay_exact_ledger"] for x in fine.values())
    elapsed=time.perf_counter()-t0; rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    criteria={f"C{i+1}":bool(v) for i,v in enumerate((C1,C2,C3,C4,C5,C6,C7,C8,elapsed<60 and rss<512))}
    sm=dict(type="summary",criteria=criteria,passed=all(criteria.values()),runs=len(rs),steps=sum(x["steps"] for x in rs),reference_fine=maxref,free_refinement=er,max_energy_fine=max(maxfine("energy_err"),maxfine("mechanical_err")),max_energy_all=max(maxall("energy_err"),maxall("mechanical_err")),max_momentum=maxall("momentum_err"),max_mass=maxall("mass_err"),max_identity=maxall("identity_err"),max_penetration=maxall("max_pen"),max_impulse_error=maxall("impulse_err"),elapsed_s=elapsed,rss_mib=rss,python=platform.python_version(),platform=platform.platform(),mujoco=mj.mj_versionString(),numpy=np.__version__,sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ("run.py","controller.py","config.json","requirements.txt")})
    lines=[json.dumps(x,separators=(",",":"),sort_keys=True,allow_nan=False) for x in [sm]+rs]; raw="\n".join(lines)+"\n"
    (ROOT/"results.jsonl").write_text(raw); print("RESULT_SHA256="+hashlib.sha256(raw.encode()).hexdigest(),flush=True)
    for line in lines: print("RESULT_LINE="+line,flush=True)
    if not sm["passed"]: raise SystemExit(1)
if __name__=="__main__": main()
