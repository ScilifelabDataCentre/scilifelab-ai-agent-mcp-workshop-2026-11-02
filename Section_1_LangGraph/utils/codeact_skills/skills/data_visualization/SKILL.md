---
name: data_visualization
description: Use this skill whenever the task involves making a figure. Produces publication-quality matplotlib charts (bar, scatter, line, concentration-time profile, heatmap) with a colorblind-safe palette, saves them under outputs/figures/, and self-checks the result with `figure_check`.
---

# Data Visualization

Every figure should be **clear, colorblind-safe, and self-contained** (readable without the surrounding text). This skill gives you a small toolkit to reach that bar without writing matplotlib boilerplate from scratch.

The recommended workflow is:

1. **Apply the publication theme** once per session.
2. **Pick a recipe** (bar / scatter / line / concentration-time / heatmap) and adapt it.
3. **Save as PNG** under `outputs/figures/` (and SVG if you want a vector copy).
4. **Run `figure_check`** to get a vision-model review — fix any issues before showing the user.

---

## 1. Global theme — apply FIRST in every session

```python
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

FIG_DIR = Path("outputs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

def set_publication_theme(base_font_size: int = 8, line_width: float = 0.75):
    """Apply a clean, publication-quality matplotlib theme."""
    matplotlib.rcParams.update({
        # Fonts
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": base_font_size,
        "axes.titlesize": base_font_size + 1,
        "axes.labelsize": base_font_size,
        "xtick.labelsize": base_font_size - 1,
        "ytick.labelsize": base_font_size - 1,
        "legend.fontsize": base_font_size - 1,
        # Axes
        "axes.linewidth": line_width,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        # Ticks
        "xtick.major.width": line_width,
        "ytick.major.width": line_width,
        "xtick.direction": "out",
        "ytick.direction": "out",
        # Save
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        # Editable text in PDF/SVG (Illustrator/Inkscape)
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        # Legend
        "legend.frameon": False,
    })

set_publication_theme()
```

Key rules baked into the theme:

- No top / right spines.
- No legend frame.
- Editable text when exported to PDF or SVG.

---

## 2. Colorblind-safe palette (Wong, 2011)

```python
PALETTE = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#CC79A7",  # pink
    "#56B4E9",  # sky blue
    "#D55E00",  # vermilion
    "#F0E442",  # yellow
    "#000000",  # black
]
```

Never use matplotlib's default colour cycle or `jet`. For >8 categories, encode shape + colour together.

---

## 3. Recipes

### Bar chart (comparing values across a few items)

```python
fig, ax = plt.subplots(figsize=(4.5, 3))
ax.bar(labels, values, color=PALETTE[:len(values)], width=0.6, linewidth=0)
ax.set_ylabel("Molecular weight (g/mol)")
ax.set_title("Comparison of drug MWs")
ax.tick_params(axis="x", rotation=20)
fig.tight_layout()
fig.savefig(FIG_DIR / "mw_comparison.png", dpi=300)
plt.close(fig)
```

### Scatter (two numeric variables)

```python
fig, ax = plt.subplots(figsize=(4, 3))
ax.scatter(x, y, s=20, alpha=0.75, color=PALETTE[0], linewidths=0)
ax.set_xlabel("LogP")
ax.set_ylabel("Molecular weight (g/mol)")
fig.tight_layout()
fig.savefig(FIG_DIR / "scatter.png", dpi=300)
plt.close(fig)
```

### Line (trend / dose-response)

```python
fig, ax = plt.subplots(figsize=(4.5, 3))
for i, (label, y) in enumerate(series.items()):
    ax.plot(x, y, color=PALETTE[i], marker="o", markersize=4, linewidth=1.2, label=label)
ax.set_xlabel("Dose (mg)")
ax.set_ylabel("Response (%)")
ax.legend(title="Compound")
fig.tight_layout()
fig.savefig(FIG_DIR / "dose_response.png", dpi=300)
plt.close(fig)
```

### Concentration-time profile (PK simulation from the `pkpd` skill)

```python
fig, ax = plt.subplots(figsize=(5, 3))
for i, (label, (t, conc)) in enumerate(profiles.items()):   # e.g. {"400 mg QD": (t, conc), ...}
    ax.plot(t / 24, conc, color=PALETTE[i], linewidth=1.2, label=label)
ax.axhline(target, color="#000000", linestyle="--", linewidth=0.75, label="Target")
ax.set_xlabel("Time (days)")
ax.set_ylabel("Plasma concentration (mg/L)")
ax.legend()
fig.tight_layout()
fig.savefig(FIG_DIR / "pk_profiles.png", dpi=300)
plt.close(fig)
```

### Heatmap (e.g. similarity matrix from the `chemistry` skill)

```python
fig, ax = plt.subplots(figsize=(4.5, 4))
im = ax.imshow(matrix.values, cmap="viridis", vmin=0, vmax=1)   # sequential, colorblind-safe colormap
ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
ax.set_yticks(range(len(matrix.index)), matrix.index)
for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        value = matrix.values[i, j]
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", color="white" if value < 0.6 else "black")
fig.colorbar(im, ax=ax, label="Tanimoto similarity")
fig.tight_layout()
fig.savefig(FIG_DIR / "similarity_heatmap.png", dpi=300)
plt.close(fig)
```

---

## 4. Saving — always close the figure

```python
fig.savefig(FIG_DIR / "plot.png", dpi=300)   # raster, good default for notebooks
fig.savefig(FIG_DIR / "plot.svg")            # vector, editable
plt.close(fig)                     # release memory
```

After saving, **tell the user the file path** — that is the deliverable.

---

## 5. Self-check (MANDATORY)

Always review the saved figure with `figure_check` and fix any issues it flags:

```python
from utils.codeact_skills.skills.data_visualization.scripts.figure_check import figure_check

feedback = figure_check("outputs/figures/mw_comparison.png")
for dimension, comment in feedback.items():
    print(f"{dimension}: {comment}")
```

`figure_check` returns a dict with five short comments:
`Readability`, `Panel Arrangement`, `Axis Labels`, `Legend`, `Color`.
If anything looks wrong, regenerate the figure with the fix applied before reporting back to the user.

---

## 6. Common mistakes to avoid

| ❌ | ✅ |
|---|---|
| Default matplotlib colors, `jet` / `rainbow` colormaps | Wong 2011 palette; `viridis` for heatmaps |
| `frameon=True` on legend | `frameon=False` (already in the theme) |
| Top/right spines visible | Removed by the theme |
| `fontsize=12` for small panels | 7–8 pt body, 9 pt panel labels |
| Axis label without units | `"Molecular weight (g/mol)"` |
| Forgetting `plt.close(fig)` | Always close after saving |
| Skipping `figure_check` | Always run it before reporting |
