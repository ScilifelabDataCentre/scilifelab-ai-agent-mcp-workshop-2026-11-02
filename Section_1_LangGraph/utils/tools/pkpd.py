"""
Ready-made PK/PD simulation tools for the drug discovery agent in Part 2 of the LangGraph workshop.

- simulate_pk:   dosing regimen + PK parameters -> plasma concentration profile (Cmax, trough, AUC, half-life, ...)
- simulate_pkpd: same, plus a direct Emax model -> drug effect over time (e.g. % target inhibition)

Model: one-compartment PK with first-order absorption (oral) or bolus input (IV), solved as an ODE system:

    dA_gut/dt     = -ka * A_gut
    dA_central/dt =  ka * A_gut - (CL / V) * A_central        C = A_central / V

    Effect(C) = Emax * C^h / (EC50^h + C^h)

Units: dose in mg, volume in L, so concentrations are in mg/L (= µg/mL; 1 mg/L = 1000 ng/mL).
Each simulation also saves a figure to `outputs/pkpd/` and returns its path.
"""

import uuid
from pathlib import Path
from typing import Literal

import numpy as np
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp, trapezoid
from langchain.tools import tool


# Internal settings: kept out of the tool signatures, so the LLM never sees (or tries to set) them
POINTS_PER_INTERVAL = 200
MAX_DOSES = 200
FIGURE_DIR = Path("outputs/pkpd")


# Helper functions
def _check_inputs(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, absorption_rate_per_h, bioavailability):
    """Return an error message the LLM can act on, or None if the inputs are valid."""
    positive = {
        'dose_mg': dose_mg, 'dosing_interval_h': dosing_interval_h, 'clearance_l_per_h': clearance_l_per_h,
        'volume_l': volume_l, 'absorption_rate_per_h': absorption_rate_per_h,
    }
    bad = [name for name, value in positive.items() if value <= 0]
    if bad:
        return f"These parameters must be > 0: {', '.join(bad)}."
    if not 1 <= n_doses <= MAX_DOSES:
        return f"n_doses must be between 1 and {MAX_DOSES}."
    if not 0 < bioavailability <= 1:
        return "bioavailability must be a fraction between 0 and 1 (e.g. 0.6 for 60%)."
    return None


def _simulate_concentrations(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l,
                             absorption_rate_per_h, bioavailability, route):
    """Simulate repeated dosing. Returns one (time, concentration) pair of arrays per dosing interval."""
    ka, ke = absorption_rate_per_h, clearance_l_per_h / volume_l

    def rhs(t, y):
        a_gut, a_central = y
        return [-ka * a_gut, ka * a_gut - ke * a_central]

    state = np.zeros(2)
    t_local = np.linspace(0, dosing_interval_h, POINTS_PER_INTERVAL + 1)
    intervals = []
    for i in range(n_doses):
        # Give the dose: into the gut (only the bioavailable fraction) or straight into plasma
        if route == "oral":
            state[0] += bioavailability * dose_mg
        else:
            state[1] += dose_mg
        sol = solve_ivp(rhs, (0, dosing_interval_h), state, t_eval=t_local, method="LSODA", rtol=1e-8, atol=1e-10)
        intervals.append((i * dosing_interval_h + sol.t, sol.y[1] / volume_l))
        state = sol.y[:, -1]
    return intervals


def _interval_metrics(t, c, dosing_interval_h):
    auc = float(trapezoid(c, t))
    i_max = int(np.argmax(c))
    return {
        'Cmax_mg_per_l': round(float(c[i_max]), 4),
        'Tmax_h_after_dose': round(float(t[i_max] - t[0]), 2),
        'Ctrough_mg_per_l': round(float(c[-1]), 4),
        'Cavg_mg_per_l': round(auc / dosing_interval_h, 4),
        'AUC_tau_mg_h_per_l': round(auc, 2),
    }


def _pk_summary(intervals, dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, route):
    half_life = np.log(2) * volume_l / clearance_l_per_h
    first, last = intervals[0], intervals[-1]
    first_metrics = _interval_metrics(*first, dosing_interval_h)
    last_metrics = _interval_metrics(*last, dosing_interval_h)
    # Steady state is reached when the trough no longer rises from one dose to the next
    at_steady_state = n_doses > 1 and intervals[-2][1][-1] / last[1][-1] > 0.97
    return {
        'regimen': f"{dose_mg} mg {route} every {dosing_interval_h} h, {n_doses} doses ({n_doses * dosing_interval_h / 24:.1f} days)",
        'half_life_h': round(half_life, 2),
        'time_to_90pct_steady_state_h': round(3.32 * half_life, 1),
        'first_dose': first_metrics,
        'last_dose': last_metrics,
        'last_dose_is_at_steady_state': bool(at_steady_state),
        'accumulation_ratio': round(last_metrics['AUC_tau_mg_h_per_l'] / first_metrics['AUC_tau_mg_h_per_l'], 2),
        'units': 'Concentrations in mg/L (1 mg/L = 1 µg/mL = 1000 ng/mL).',
    }


def _save_figure(fig: Figure, prefix: str) -> str:
    try:
        FIGURE_DIR.mkdir(parents=True, exist_ok=True)
        path = FIGURE_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        return str(path)
    except OSError as e:
        return f"Figure could not be saved ({e})."


# Tool 1: PK SIMULATION
@tool(parse_docstring=True)
def simulate_pk(
    dose_mg: float,
    dosing_interval_h: float,
    n_doses: int,
    clearance_l_per_h: float,
    volume_l: float,
    absorption_rate_per_h: float = 1.0,
    bioavailability: float = 1.0,
    route: Literal["oral", "iv_bolus"] = "oral",
    target_conc_mg_per_l: float | None = None,
) -> dict:
    """Simulate plasma concentrations of a drug over a repeated dosing regimen (one-compartment PK model).

    Use apparent oral values (CL/F, V/F) with bioavailability=1 if that is what the literature reports.

    Args:
        dose_mg: Dose given at each administration, in mg.
        dosing_interval_h: Time between doses in hours, e.g. 24 for once daily, 12 for twice daily.
        n_doses: Number of doses to simulate, e.g. 14 for two weeks of once-daily dosing.
        clearance_l_per_h: Clearance (CL) in L/h.
        volume_l: Volume of distribution (V) in L.
        absorption_rate_per_h: First-order absorption rate constant (ka) in 1/h. Ignored for IV dosing.
        bioavailability: Fraction of an oral dose reaching the circulation (F), between 0 and 1. Ignored for IV dosing.
        route: How the drug is given, 'oral' or 'iv_bolus'.
        target_conc_mg_per_l: Optional target concentration in mg/L, e.g. a minimum effective concentration.

    Returns:
        Half-life, time to steady state, Cmax/Tmax/trough/AUC after the first and the last dose, accumulation ratio, optional target coverage and the path of a saved concentration-time plot.
    """
    error = _check_inputs(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, absorption_rate_per_h, bioavailability)
    if error:
        return {'error': error}

    intervals = _simulate_concentrations(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l,
                                         absorption_rate_per_h, bioavailability, route)
    summary = _pk_summary(intervals, dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, route)

    if target_conc_mg_per_l is not None:
        c_last = intervals[-1][1]
        summary['target'] = {
            'target_conc_mg_per_l': target_conc_mg_per_l,
            'percent_of_last_interval_above_target': round(100 * float(np.mean(c_last >= target_conc_mg_per_l)), 1),
            'trough_above_target': bool(c_last[-1] >= target_conc_mg_per_l),
        }

    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    for t, c in intervals:
        ax.plot(t, c, color="tab:blue")
    if target_conc_mg_per_l is not None:
        ax.axhline(target_conc_mg_per_l, color="tab:red", linestyle="--", label="target")
        ax.legend()
    ax.set(xlabel="Time (h)", ylabel="Concentration (mg/L)", title=summary['regimen'])
    summary['figure'] = _save_figure(fig, "pk")
    return summary


# Tool 2: PK/PD SIMULATION
@tool(parse_docstring=True)
def simulate_pkpd(
    dose_mg: float,
    dosing_interval_h: float,
    n_doses: int,
    clearance_l_per_h: float,
    volume_l: float,
    ec50_mg_per_l: float,
    absorption_rate_per_h: float = 1.0,
    bioavailability: float = 1.0,
    route: Literal["oral", "iv_bolus"] = "oral",
    emax_percent: float = 100.0,
    hill: float = 1.0,
    target_effect_percent: float = 50.0,
) -> dict:
    """Simulate drug concentrations AND the resulting effect (e.g. % target inhibition) over a dosing regimen.

    PK: one-compartment model. PD: direct Emax model, effect = Emax * C^hill / (EC50^hill + C^hill).

    Args:
        dose_mg: Dose given at each administration, in mg.
        dosing_interval_h: Time between doses in hours, e.g. 24 for once daily, 12 for twice daily.
        n_doses: Number of doses to simulate, e.g. 14 for two weeks of once-daily dosing.
        clearance_l_per_h: Clearance (CL) in L/h.
        volume_l: Volume of distribution (V) in L.
        ec50_mg_per_l: Concentration giving half of the maximum effect (EC50 or IC50), in mg/L.
        absorption_rate_per_h: First-order absorption rate constant (ka) in 1/h. Ignored for IV dosing.
        bioavailability: Fraction of an oral dose reaching the circulation (F), between 0 and 1. Ignored for IV dosing.
        route: How the drug is given, 'oral' or 'iv_bolus'.
        emax_percent: Maximum possible effect in percent (default 100).
        hill: Hill coefficient describing the steepness of the concentration-effect curve (default 1).
        target_effect_percent: Effect level that should be maintained, in percent (default 50).

    Returns:
        The PK summary plus the effect at peak and trough, the average effect and the percentage of time above the target effect, for the first and the last dose, and the path of a saved plot.
    """
    error = _check_inputs(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, absorption_rate_per_h, bioavailability)
    if error:
        return {'error': error}
    if ec50_mg_per_l <= 0 or hill <= 0 or not 0 < emax_percent <= 100:
        return {'error': 'ec50_mg_per_l and hill must be > 0, and emax_percent between 0 and 100.'}

    def effect(c):
        return emax_percent * c**hill / (ec50_mg_per_l**hill + c**hill)

    def pd_metrics(c):
        e = effect(c)
        return {
            'effect_at_peak_percent': round(float(e.max()), 1),
            'effect_at_trough_percent': round(float(e[-1]), 1),
            'mean_effect_percent': round(float(e.mean()), 1),
            'percent_of_interval_above_target_effect': round(100 * float(np.mean(e >= target_effect_percent)), 1),
        }

    intervals = _simulate_concentrations(dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l,
                                         absorption_rate_per_h, bioavailability, route)
    summary = _pk_summary(intervals, dose_mg, dosing_interval_h, n_doses, clearance_l_per_h, volume_l, route)
    summary['pd_model'] = f"Emax={emax_percent}%, EC50={ec50_mg_per_l} mg/L, hill={hill}"
    summary['target_effect_percent'] = target_effect_percent
    summary['first_dose_effect'] = pd_metrics(intervals[0][1])
    summary['last_dose_effect'] = pd_metrics(intervals[-1][1])

    fig = Figure(figsize=(8, 6))
    ax_pk, ax_pd = fig.subplots(2, 1, sharex=True)
    for t, c in intervals:
        ax_pk.plot(t, c, color="tab:blue")
        ax_pd.plot(t, effect(c), color="tab:green")
    ax_pk.axhline(ec50_mg_per_l, color="grey", linestyle=":", label="EC50")
    ax_pk.legend()
    ax_pd.axhline(target_effect_percent, color="tab:red", linestyle="--", label="target effect")
    ax_pd.legend()
    ax_pk.set(ylabel="Concentration (mg/L)", title=summary['regimen'])
    ax_pd.set(xlabel="Time (h)", ylabel="Effect (%)", ylim=(0, 100))
    summary['figure'] = _save_figure(fig, "pkpd")
    return summary
