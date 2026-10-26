---
name: pkpd
description: Pharmacokinetic / pharmacodynamic simulation with SciPy. Concentration-time profiles for repeated oral or IV dosing (Cmax, trough, AUC, half-life, steady state), Emax effect models, dose finding, regimen comparison, loading or missed doses and custom compartment models. Use for any dosing, exposure or target-coverage question.
---

# PK/PD simulation

This skill uses the **same model and units as the ReAct agent's PK/PD tools** (`utils/tools/pkpd.py`), so both agents give the same numbers. Use the ready-made functions for a single regimen; use the recipes below for dose sweeps, unusual dosing schedules and other models.

**Units everywhere:** dose in mg, volume in L, clearance in L/h, time in h → concentrations in **mg/L** (= µg/mL; 1 mg/L = 1000 ng/mL).

**Never invent PK parameters.** Use the values the user gives, or find them with the `literature` skill and cite the source. Literature often reports *apparent* oral values (CL/F, V/F): use them with bioavailability F = 1.

---

## 1. Ready-made functions (one regimen, with a saved plot)

```python
from utils.tools.pkpd import simulate_pk, simulate_pkpd

pk = simulate_pk.invoke({
    "dose_mg": 400, "dosing_interval_h": 24, "n_doses": 14,
    "clearance_l_per_h": 14.3, "volume_l": 347, "absorption_rate_per_h": 0.6,
    "target_conc_mg_per_l": 1.0,                      # optional
})
# -> {'half_life_h', 'time_to_90pct_steady_state_h', 'first_dose': {...}, 'last_dose': {'Cmax_mg_per_l',
#     'Tmax_h_after_dose', 'Ctrough_mg_per_l', 'Cavg_mg_per_l', 'AUC_tau_mg_h_per_l'},
#     'last_dose_is_at_steady_state', 'accumulation_ratio', 'target': {...}, 'figure': 'outputs/pkpd/...png'}

pkpd = simulate_pkpd.invoke({..., "ec50_mg_per_l": 0.5, "hill": 1.0, "target_effect_percent": 50})
# -> same PK summary + 'first_dose_effect' / 'last_dose_effect': {'effect_at_peak_percent',
#     'effect_at_trough_percent', 'mean_effect_percent', 'percent_of_interval_above_target_effect'}
```

Other arguments: `bioavailability` (0–1, default 1), `route` (`"oral"` or `"iv_bolus"`), `emax_percent` (default 100).
Each call saves a figure. For many simulations (sweeps), use the recipes below instead.

---

## 2. Core simulator for custom work

The model is a set of ODEs for drug **amounts** (mg) in each compartment; doses are added at the start of each dosing interval. Changing `rhs` changes the model; changing `doses` changes the schedule.

```python
import numpy as np
from scipy.integrate import solve_ivp, trapezoid

def simulate(rhs, n_compartments: int, doses: list[float], tau_h: float, dose_compartment: int = 0, points: int = 200):
    """Give doses[i] mg into `dose_compartment` at t = i * tau_h (use 0 for a missed dose).
    Returns time (h) and amounts (mg) with shape (n_compartments, n_times)."""
    y = np.zeros(n_compartments)
    t_local = np.linspace(0, tau_h, points + 1)
    times, amounts = [], []
    for i, dose in enumerate(doses):
        y[dose_compartment] += dose
        sol = solve_ivp(rhs, (0, tau_h), y, t_eval=t_local, method="LSODA", rtol=1e-8, atol=1e-10)
        times.append(i * tau_h + sol.t[:-1])
        amounts.append(sol.y[:, :-1])
        y = sol.y[:, -1].copy()
    times.append([len(doses) * tau_h])
    amounts.append(y[:, None])
    return np.concatenate(times), np.concatenate(amounts, axis=1)


def one_compartment_oral(cl: float, v: float, ka: float):
    """Compartments: 0 = gut, 1 = plasma. Same model as simulate_pk."""
    ke = cl / v
    return lambda t, y: [-ka * y[0], ka * y[0] - ke * y[1]]


def last_interval(t, conc, tau_h: float, n_doses: int) -> dict:
    """Metrics over the last dosing interval (= steady state if enough doses were given)."""
    mask = t >= (n_doses - 1) * tau_h - 1e-9
    tt, cc = t[mask], conc[mask]
    auc = trapezoid(cc, tt)
    return {"Cmax": cc.max(), "Ctrough": cc[-1], "Cavg": auc / tau_h, "AUC_tau": auc}


# Example: imatinib 400 mg once daily for 14 days (CL/F 14.3 L/h, V/F 347 L, ka 0.6 1/h)
CL, V, KA, F = 14.3, 347, 0.6, 1.0
t, amounts = simulate(one_compartment_oral(CL, V, KA), 2, [F * 400] * 14, tau_h=24)
conc = amounts[1] / V                                   # plasma concentration (mg/L)
last_interval(t, conc, 24, 14)                          # Ctrough ≈ 0.733 mg/L, same as simulate_pk
```

Useful formulas: half-life = ln(2) · V / CL; steady state is ~90% reached after 3.3 half-lives and ~97% after 5; at steady state AUC_tau = F · dose / CL.

---

## 3. Recipes

### Dose finding (sweep, then pick the lowest dose that meets the target)

```python
import pandas as pd

rows = []
for dose in range(100, 1001, 100):
    t, a = simulate(one_compartment_oral(CL, V, KA), 2, [F * dose] * 14, tau_h=24)
    rows.append({"dose_mg": dose, **last_interval(t, a[1] / V, 24, 14)})
sweep = pd.DataFrame(rows).round(3)
target = 1.0                                             # mg/L trough target
print(sweep)
print("Lowest dose reaching the target:", sweep.loc[sweep.Ctrough >= target, "dose_mg"].min(), "mg")
```

### Loading dose and missed dose

```python
schedules = {
    "standard":         [400] * 14,
    "loading dose":     [800] + [400] * 13,
    "missed dose day 8": [400] * 7 + [0] + [400] * 6,
}
for name, doses in schedules.items():
    t, a = simulate(one_compartment_oral(CL, V, KA), 2, [F * d for d in doses], tau_h=24)
    c = a[1] / V
    daily_troughs = c[np.isin(np.round(t, 6), np.arange(24, 24 * 15, 24))]   # concentration just before each next dose
    print(f"{name:18s} troughs (mg/L):", np.round(daily_troughs, 2))
```

### Two-compartment model (drug distributes into tissue)

```python
def two_compartment_oral(cl: float, v1: float, q: float, v2: float, ka: float):
    """Compartments: 0 = gut, 1 = central (plasma, volume v1), 2 = peripheral (volume v2); q = intercompartmental clearance (L/h)."""
    return lambda t, y: [
        -ka * y[0],
        ka * y[0] - (cl / v1) * y[1] - (q / v1) * y[1] + (q / v2) * y[2],
        (q / v1) * y[1] - (q / v2) * y[2],
    ]

t, a = simulate(two_compartment_oral(cl=10, v1=50, q=20, v2=200, ka=1.0), 3, [300] * 7, tau_h=24)
conc = a[1] / 50                                        # plasma concentration = central amount / v1
```

### IV dosing

Put the dose straight into plasma and ignore absorption: `simulate(one_compartment_oral(CL, V, KA), 2, doses, tau_h, dose_compartment=1)`.

### Pharmacodynamics: Emax model and target coverage

```python
def emax_effect(conc, ec50: float, emax: float = 100.0, hill: float = 1.0):
    """Direct Emax model (same as simulate_pkpd): effect in % for a concentration in mg/L."""
    return emax * conc**hill / (ec50**hill + conc**hill)

effect = emax_effect(conc, ec50=0.5)
mask = t >= (7 - 1) * 24                                # last dosing interval
print("Time above 50% effect in the last interval:", round(100 * np.mean(effect[mask] >= 50), 1), "%")
```

The time grid is uniform, so the fraction of points above a threshold equals the fraction of time.

### Plotting

Use the `data_visualization` skill. A concentration-time plot should have time in h on the x-axis, concentration in mg/L on the y-axis, and the target as a dashed horizontal line. Save it under `outputs/`.

---

## Pitfalls

- Check units before simulating (ng/mL vs mg/L, minutes vs hours, mL/min vs L/h: 1 mL/min = 0.06 L/h).
- Simulate long enough to reach steady state (≥ 5 half-lives) before reporting steady-state values.
- A **trough** is the concentration just before the next dose. To judge recovery after a missed or changed dose, compare trough with trough (as in the missed-dose recipe), not with the continuous curve, which rises above the trough level right after every dose.
- These are typical-patient simulations: real patients vary a lot (often 30–60% variability in CL). Say so when making dosing statements.
