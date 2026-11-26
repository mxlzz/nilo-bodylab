"""Trusted experimental controller; only local observations and prescribed program."""
def choose(observation,tick,program,period):
    if set(observation)!={"rays","touch","touch_impulse_Ns","fuel_kg","velocity_body"}:
        raise ValueError("unexpected observation schema")
    if program["controller"]=="idle":
        return {"u":[0.,0.],"exchange":False}
    t=tick*period
    if program["retreat_at"] is not None and t>=program["retreat_at"]:
        u=[-float(a) for a in program["u"]]
    elif t<program["drive_until"]:
        u=list(program["u"])
    else:
        u=[0.,0.]
    request=tick in program["exchange_at"]
    if program["controller"]=="contact":
        request=request and observation["touch"] and sum(v*v for v in observation["velocity_body"])<=.01**2
    return {"u":u,"exchange":request}
