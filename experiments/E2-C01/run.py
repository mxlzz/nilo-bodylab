import argparse, hashlib, json, math, platform, resource, sys, time
from pathlib import Path


def initial(c,k):
    return dict(F=c['fuel'],X=c['externalFuel'],W=0.,m=c['water'],x=c['externalWater'],v=0.,Jw=0.,H=(k['Cd']+k['cp']*c['water'])*(c['T']-k['Tr']),B=0.,U=0.)


def temperature(s,k):
    return k['Tr']+s['H']/(k['Cd']+k['cp']*s['m'])


def ledger(s,k):
    return (s['F']+s['X']+s['W'],s['m']+s['x']+s['v'],k['q']*(s['F']+s['X'])+s['Jw']+s['H']+s['B']+s['U']+k['cp']*s['x']*(k['Tin']-k['Tr']))


def run(c,a,L,dt,k,snapshot=None,start=0):
    s=initial(c,k) if snapshot is None else dict(snapshot)
    origin=ledger(initial(c,k),k)
    scales=[max(1,origin[0]),max(1e-6,origin[1]),max(1,origin[2])]
    residual=[0.,0.,0.]
    valid=True
    ends=[]
    steps=0
    def inspect():
        nonlocal valid
        T=temperature(s,k)
        valid &= 280<=T<=380 and k['R0']*(1+a*(T-k['Tref']))>0 and min(s[z] for z in ('F','X','W','m','x','v','Jw'))>=0
        for i,z in enumerate(ledger(s,k)):
            residual[i]=max(residual[i],abs(z-origin[i])/scales[i])
    inspect()
    for dur,Ta,on,w,r,reqF,reqW in c['segments'][start:]:
        f,u=min(s['X'],reqF),min(s['x'],reqW)
        s['X']-=f;s['F']+=f;s['x']-=u;s['m']+=u;s['H']+=k['cp']*u*(k['Tin']-k['Tr'])
        valid &= 0<=f<=reqF and 0<=u<=reqW
        inspect()
        n=round(dur/dt)
        assert n*dt==dur
        for _ in range(n):
            T=temperature(s,k)
            R=k['R0']*(1+a*(T-k['Tref']))
            I=(k['V']-k['K']*w)/R if on else 0.
            want=k['V']*I*dt/k['q']
            used=min(s['F'],want)
            j=k['q']*used*k['K']*w/k['V']
            g=k['q']*used-j
            loss=min(s['m'],r*dt)
            e=loss*(k['cp']*(T-k['Tr'])+L)
            b=k['G']*(T-Ta)*dt
            s['F']-=used;s['W']+=used;s['Jw']+=j
            s['H']+=g-b-e;s['B']+=b;s['U']+=e;s['m']-=loss;s['v']+=loss
            valid &= 0<=used<=want and 0<=loss<=r*dt and j>=0 and g>=0
            inspect()
            steps+=1
        T=temperature(s,k)
        probe=k['K']*4*(k['V']-k['K']*4)/(k['R0']*(1+a*(T-k['Tref'])))
        ends.append(dict(s=dict(s),T=T,probe=probe,effective=j/dt,acceptedF=f,acceptedW=u,rejectedF=reqF-f,rejectedW=reqW-u))
    return dict(ends=ends,residual=residual,valid=valid,steps=steps)


def reference(c,a,L,k):
    T,m,J=c['T'],c['water'],0.
    x=c['externalWater']
    ends=[]
    for dur,Ta,on,w,r,_,reqW in c['segments']:
        u=min(x,reqW);x-=u
        C=k['Cd']+k['cp']*m
        T=(C*T+k['cp']*u*k['Tin'])/(C+k['cp']*u);m+=u
        wet=min(dur,m/r) if r else 0.
        for span,rate in ((wet,r),(dur-wet,0.)):
            if not span: continue
            C=k['Cd']+k['cp']*m
            if not a:
                I=(k['V']-k['K']*w)/k['R0'] if on else 0.
                p=I*I*k['R0'];eq=Ta+(p-L*rate)/k['G']
                if rate:
                    C1=C-k['cp']*rate*span
                    T=eq+(T-eq)*(C1/C)**(k['G']/(k['cp']*rate))
                else:
                    T=eq+(T-eq)*math.exp(-k['G']*span/C)
                J+=k['K']*w*I*span
            else:
                def deriv(t,z):
                    R=k['R0']*(1+a*(z-k['Tref']))
                    I=(k['V']-k['K']*w)/R if on else 0.
                    return (I*I*R-k['G']*(z-Ta)-L*rate)/(C-k['cp']*rate*t),k['K']*w*I
                n=math.ceil(span*4096);h=span/n
                for i in range(n):
                    t=i*h
                    A,p=deriv(t,T);B,q=deriv(t+h/2,T+h*A/2);D,rj=deriv(t+h/2,T+h*B/2);E,sj=deriv(t+h,T+h*D)
                    T+=h*(A+2*B+2*D+E)/6;J+=h*(p+2*q+2*rj+sj)/6
            m-=min(m,rate*span)
        ends.append(dict(T=T,Jw=J))
    return ends


def main():
    t=time.perf_counter()
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    data=Path(args.config).read_bytes();k=json.loads(data);lim=k['limits'];fine=min(k['dt']);records=[]
    for c in k['cases']:
        for a in (0.,k['alpha']):
            for L in (0.,k['Lv']):
                ref=reference(c,a,L,k) if c['id']!='deplete-refill' else None
                for dt in k['dt']:
                    z=run(c,a,L,dt,k)
                    errT=max(abs(x['T']-y['T']) for x,y in zip(z['ends'],ref)) if ref else None
                    errJ=max(abs(x['s']['Jw']-y['Jw'])/max(1,abs(y['Jw'])) for x,y in zip(z['ends'],ref)) if ref else None
                    replay=None
                    if dt==fine:
                        snap=json.loads(json.dumps(z['ends'][0]['s']))
                        replay=run(c,a,L,dt,k,snap,1)['ends']==z['ends'][1:]
                    records.append(dict(id=c['id'],alpha=a,latent=L,dt=dt,ref=ref,errT=errT,errJ=errJ,replay=replay,**z))
    f={(z['id'],z['alpha'],z['latent']):z['ends'] for z in records if z['dt']==fine}
    def end(id,a,L,i=-1):return f[id,a,L][i]
    def err(dt,key):return max(z[key] for z in records if z['dt']==dt and z[key] is not None)
    a,L=k['alpha'],k['Lv'];eps=1e-10
    mx=[max(z['residual'][i] for z in records) for i in range(3)]
    ft,ct=err(fine,'errT'),err(2*fine,'errT');fj=err(fine,'errJ')
    def phase_equal(id,v):
        return all(abs(x['T']-y['T'])<=eps and abs(x['s']['Jw']-y['s']['Jw'])<=eps for x,y in zip(f[id,v,0.],f[id,v,L]))
    def work_delta(v):return end('wet',v,L,0)['s']['Jw']-end('wet',v,0.,0)['s']['Jw']
    interaction=work_delta(a)-work_delta(0.)
    def deplete(v,l):
        p,q,r,s=f['deplete-refill',v,l];P,Q,R,S=[z['s'] for z in (p,q,r,s)]
        return P['F']<=1e-12 and P['m']<=1e-12 and all(Q[key]==P[key] for key in ('Jw','v','U')) and q['effective']==0 and r['acceptedF']==1 and r['rejectedF']>0 and abs(r['acceptedW']-0.00004)<=1e-12 and r['rejectedW']>0 and R['Jw']==Q['Jw'] and S['Jw']>R['Jw'] and S['v']>R['v'] and all(abs(z['s']['Jw']-.4*k['q']*z['s']['W'])<=1e-9 for z in (p,q,r,s))
    wall=time.perf_counter()-t;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    checks=dict(balances=max(mx)<=lim['balance'],admissible=all(z['valid'] for z in records),reference=ft<=lim['temp_K'] and fj<=lim['work_rel'],convergence=ft<=lim['convergence']*ct or max(ft,ct)<=1e-8,negative_controls=all(phase_equal(id,v) for id in ('sealed','dry') for v in (0.,a)) and all(end('stall',v,l,0)['s']['Jw']==0 and end('stall',v,l,0)['s']['W']>0 for v in (0.,a) for l in (0.,L)),interaction=abs(end('wet',a,L,0)['s']['v']-end('wet',a,0.,0)['s']['v'])<=1e-12 and end('wet',a,L,0)['T']<end('wet',a,0.,0)['T'] and work_delta(a)>=lim['interaction_J'] and abs(work_delta(0.))<=eps and interaction>lim['interaction_J'],depletion_refill=all(deplete(v,l) for v in (0.,a) for l in (0.,L)),replay=all(z['replay'] is True for z in records if z['dt']==fine),resources=wall<=lim['wall_s'] and rss<=lim['rss_MiB'])
    summary=dict(checks=checks,verdict='H1_conditional' if all(checks.values()) else 'inconclusive',runs=len(records),steps=sum(z['steps'] for z in records),balances=mx,fine_error_K=ft,coarse_error_K=ct,work_error=fj,interaction_J=interaction,work_delta_J=work_delta(a),control_delta_J=work_delta(0.),wall_s=wall,rss_MiB=rss,python=sys.version,platform=platform.platform(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=hashlib.sha256(data).hexdigest())
    Path(args.out).write_text(json.dumps(dict(summary=summary,records=records),separators=(',',':'),allow_nan=False)+'\n');print(json.dumps(summary,indent=2));return 0 if all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
