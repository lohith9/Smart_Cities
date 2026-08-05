"""
v2_04_marl.py
Multi-Agent Reinforcement Learning signal control (PressLight-inspired).

We implement a lightweight MARL controller in which each of the 10 junctions
runs an independent tabular Q-learning agent. Following Wei et al. (KDD 2019,
'PressLight: Learning Max Pressure Control to Coordinate Traffic Signals in
Arterial Network', doi:10.1145/3292500.3330949), the local reward is driven by
the *pressure* at the junction. This implementation uses a simplified,
undirected pressure - own served flow minus the mean over graph neighbours -
rather than PressLight's directed upstream-minus-downstream sum:

    pressure(i,t) = q(i,t) - mean_{j in neighbours(i)} q(j,t)

State: (own_flow, neighbour_flow, hour_phase), each discretised into 5 bins
(flow edges 0/250/450/700/1100/1700; hour edges 0/6/10/16/20/24), giving 125
states. An earlier version of this header described the discretisation as
three-level (low/med/high).
Action: choose green split bias in {-1, 0, +1}, applied as a -8% / 0% / +8%
change to the flow the junction serves.
Reward: -|pressure|/200 - 0.5 * delay_proxy. An earlier version of this header
gave the reward as "-|pressure| - 0.05 * delay_proxy", which is not what
train_marl implements.

Compared baselines:
  - Fixed-time:      static signal split, no adaptation
  - Greedy heuristic: largest-queue gets longer green
  - MARL (tabular Q): learned distributed policy

Outputs:
  ../data/marl_results.json
  ../data/marl_learning_curve.csv
"""
import json, time, random
import numpy as np
import pandas as pd

from pathlib import Path
import os as _os
ROOT = Path(__file__).resolve().parent.parent
DATA = str(ROOT / "data")
_os.makedirs(DATA, exist_ok=True)
arr = np.load(f"{DATA}/v2_network.npz", allow_pickle=True)
A   = np.load(f"{DATA}/v2_adjacency.npy")
flow = arr["flow"]
hod  = arr["hour_of_day"]
T, N = flow.shape

# Network neighbour helpers
neighbours = [list(np.where((A[n] > 0) & (np.arange(N) != n))[0]) for n in range(N)]

# --- State discretisation ---
def discretise(values, bins):
    return np.clip(np.digitize(values, bins) - 1, 0, len(bins) - 1).astype(int)

flow_bins = [0, 250, 450, 700, 1100, 1700]   # 5 bins
hour_bins = [0, 6, 10, 16, 20, 24]            # 5 bins
N_FLOW_STATES = len(flow_bins) - 1
N_HOUR_STATES = len(hour_bins) - 1
N_ACTIONS     = 3   # {-1, 0, +1} green-split shift

# Encode (own_flow, mean_neighbour_flow, hour_phase) -> integer state
def state_id(own_flow, nbr_flow, hour):
    o = discretise(np.array([own_flow]), flow_bins)[0]
    n = discretise(np.array([nbr_flow]), flow_bins)[0]
    h = discretise(np.array([hour]), hour_bins)[0]
    return ((o * N_FLOW_STATES) + n) * N_HOUR_STATES + h

N_STATES = N_FLOW_STATES * N_FLOW_STATES * N_HOUR_STATES

# --- Reward model (proxy) ---
# Delay proxy: when flow exceeds half capacity, delay grows quadratically
def delay_proxy(f, cap):
    v = f / cap
    return np.maximum(0, v - 0.5) ** 2 * 60   # min/km
CAP = 1300  # approx mean capacity

def pressure(own_q, nbr_q):
    """Difference between own queue and mean neighbour queue (PressLight)."""
    return own_q - np.mean(nbr_q)

# --- Episode simulator ---
def run_episode(policy_fn, n_steps=200, log_curve=False, seed=None):
    """Roll a synthetic episode where each step is an hour drawn from the dataset.
       The 'controller' adjusts a green-split factor that re-scales the effective
       flow each agent can serve. Returns per-step delay & emissions proxy.
    """
    r = random.Random(seed if seed is not None else 1)
    delays = []
    presures = []
    for step in range(n_steps):
        t = r.randrange(T)
        f = flow[t].copy()
        h = hod[t]
        # Each agent decides green-split shift
        actions = np.zeros(N, dtype=int)
        for n in range(N):
            nbr_f = np.mean(f[neighbours[n]]) if neighbours[n] else f[n]
            s = state_id(f[n], nbr_f, h)
            actions[n] = policy_fn(n, s)
        # Apply action: shift = -1 -> -8% served flow, 0 -> baseline, +1 -> +8%
        green_factor = 1.0 + (actions - 1) * 0.08
        served = f * green_factor
        d = delay_proxy(served, CAP)
        # Compute pressure across network
        for n in range(N):
            nbr_q = served[neighbours[n]] if neighbours[n] else np.array([served[n]])
            presures.append(abs(pressure(served[n], nbr_q)))
        delays.append(d.mean())
    return float(np.mean(delays)), float(np.mean(presures))

# --- Policies ---
def fixed_policy(n, s):
    return 1   # always neutral

def greedy_policy(n, s):
    # Decode: state = ((o*N)+n2)*N_HOUR + h ; we need own o vs nbr n2
    rem = s // N_HOUR_STATES
    nbr_o = rem % N_FLOW_STATES
    own_o = rem // N_FLOW_STATES
    if own_o > nbr_o:    return 2   # bias toward us (longer green)
    if own_o < nbr_o:    return 0
    return 1

# Q-learning
def train_marl(n_episodes=50, n_steps=120, gamma=0.9, alpha=0.2,
               eps_start=0.6, eps_end=0.05):
    Q = np.zeros((N, N_STATES, N_ACTIONS))
    curve = []
    r = random.Random(20260516)
    for ep in range(n_episodes):
        eps = eps_start + (eps_end - eps_start) * ep / max(1, n_episodes - 1)
        ep_delays = []
        for step in range(n_steps):
            t = r.randrange(T)
            f = flow[t].copy()
            h = hod[t]
            states = np.zeros(N, dtype=int)
            actions = np.zeros(N, dtype=int)
            for n in range(N):
                nbr_f = np.mean(f[neighbours[n]]) if neighbours[n] else f[n]
                s = state_id(f[n], nbr_f, h)
                states[n] = s
                if r.random() < eps:
                    actions[n] = r.randrange(N_ACTIONS)
                else:
                    actions[n] = int(np.argmax(Q[n, s]))
            green_factor = 1.0 + (actions - 1) * 0.08
            served = f * green_factor
            d_arr = delay_proxy(served, CAP)
            ep_delays.append(d_arr.mean())
            # Compute next state from a re-sampled near-future condition
            t_next = (t + 1) % T
            f_next = flow[t_next]
            h_next = hod[t_next]
            for n in range(N):
                nbr_q = served[neighbours[n]] if neighbours[n] else np.array([served[n]])
                press = abs(pressure(served[n], nbr_q))
                reward = -press / 200.0 - 0.5 * d_arr[n]
                nbr_f_next = np.mean(f_next[neighbours[n]]) if neighbours[n] else f_next[n]
                s_next = state_id(f_next[n], nbr_f_next, h_next)
                target = reward + gamma * Q[n, s_next].max()
                Q[n, states[n], actions[n]] += alpha * (target - Q[n, states[n], actions[n]])
        curve.append({"episode": ep, "epsilon": eps, "mean_delay": float(np.mean(ep_delays))})
    return Q, curve

t0 = time.time()
Q, curve = train_marl(n_episodes=50, n_steps=120)
t_train = time.time() - t0
print(f"MARL training: {t_train:.1f}s")

# Evaluate all three policies with the same seed for fairness
def eval_policy(name, policy_fn):
    delays = []
    pressures = []
    for trial in range(5):
        d, p = run_episode(policy_fn, n_steps=400, seed=100 + trial)
        delays.append(d); pressures.append(p)
    return {
        "policy": name,
        "mean_delay": float(np.mean(delays)),
        "delay_std":  float(np.std(delays)),
        "mean_pressure": float(np.mean(pressures)),
    }

def marl_policy_fn(n, s):
    return int(np.argmax(Q[n, s]))

results = {
    "training_time_s": t_train,
    "policies": [
        eval_policy("fixed_time", fixed_policy),
        eval_policy("greedy_pressure", greedy_policy),
        eval_policy("marl_qlearning", marl_policy_fn),
    ],
    "learning_curve": curve,
}

print("\n=== MARL vs baselines ===")
base = results["policies"][0]["mean_delay"]
for p in results["policies"]:
    red = 100.0 * (base - p["mean_delay"]) / base
    print(f"  {p['policy']:18s}  mean_delay={p['mean_delay']:.4f}  pressure={p['mean_pressure']:.2f}  reduction_vs_fixed={red:+.2f}%")

with open(f"{DATA}/marl_results.json", "w") as f:
    json.dump(results, f, indent=2)
pd.DataFrame(curve).to_csv(f"{DATA}/marl_learning_curve.csv", index=False)
print("\nSaved -> marl_results.json, marl_learning_curve.csv")
