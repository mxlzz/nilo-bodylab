"""Trusted experimental controllers. No physics or evaluator references."""
def choose(observation, tick, program, mode):
    if set(observation) != {"rays", "touch", "fuel_kg"}:
        raise ValueError("unexpected observation schema")
    if mode == "idle":
        return {"pull": 0., "exchange": 0.}
    if mode != "script":
        raise ValueError("unknown experimental controller")
    return {"pull": float(program["pull"]) if tick in program["pull_ticks"] else 0.,
            "exchange": float(program["exchange"]) if tick == 0 else 0.}
