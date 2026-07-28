import numpy as np, random
from pathlib import Path
DATA=str(Path(__file__).resolve().parent.parent / "data")
arr=np.load(f"{DATA}/v2_network.npz",allow_pickle=True)
A=np.load(f"{DATA}/v2_adjacency.npy")
flow=arr["flow"]; hod=arr["hour_of_day"]; T,N=flow.shape
CAP=1300
def delay_proxy(f,cap):
    v=f/cap; return np.maximum(0,v-0.5)**2*60

# 1) MONOTONICITY: is delay_proxy strictly decreasing as we throttle?
print("=== (1) delay_proxy vs green_factor at representative loads ===")
gf=[0.92,1.00,1.08]
for load in [0.5,0.7,0.9,1.0,1.2]:
    f=load*CAP
    ds=[delay_proxy(np.array([f*g]),CAP)[0] for g in gf]
    print(f"  flow/cap={load:>4}: throttle(0.92)={ds[0]:7.3f}  neutral(1.0)={ds[1]:7.3f}  boost(1.08)={ds[2]:7.3f}  -> argmin action = {['THROTTLE','neutral','boost'][int(np.argmin(ds))]}")

# 2) Replicate run_episode and test naive constant policies
def run_episode(action_const, n_steps=400, seed=None):
    r=random.Random(seed if seed is not None else 1)
    delays=[]
    for step in range(n_steps):
        t=r.randrange(T); f=flow[t].copy()
        actions=np.full(N,action_const,dtype=int)
        gfac=1.0+(actions-1)*0.08
        served=f*gfac
        delays.append(delay_proxy(served,CAP).mean())
    return float(np.mean(delays))

print("\n=== (2) constant-action policies (same eval seeds 100-104) ===")
for name,act in [("fixed/neutral (1.0x)",1),("ALWAYS THROTTLE (0.92x)",0),("always boost (1.08x)",2)]:
    ds=[run_episode(act,seed=100+tr) for tr in range(5)]
    print(f"  {name:24s} mean_delay={np.mean(ds):.4f}")
base=np.mean([run_episode(1,seed=100+tr) for tr in range(5)])
thr =np.mean([run_episode(0,seed=100+tr) for tr in range(5)])
print(f"\n  Reduction of ALWAYS-THROTTLE vs fixed = {100*(base-thr)/base:+.2f}%")
print("  (MARL reported reduction = +42.96%)")

# 3) what fraction of served stays above the 0.5 threshold (where proxy is active)?
print("\n=== (3) load distribution (only loads >0.5*cap incur proxy delay) ===")
v=flow/CAP
print(f"  mean flow/cap={v.mean():.3f}  frac>0.5={np.mean(v>0.5):.3f}  max={v.max():.3f}")
