---
name: chemistry
description: Small-molecule cheminformatics with RDKit. Resolve compound names or IDs to SMILES, remove salts, compute physicochemical properties, check drug-likeness rules (Lipinski, Veber), compare structural similarity (Tanimoto) and search for substructures. Use for any question about a compound's structure, properties, drug-likeness or analogues.
---

# Chemistry (small molecules)

This skill wraps the **same functions as the ReAct agent's chemistry tools** (`utils/tools/chemistry.py`), so both agents give consistent numbers. Use the ready-made functions first; use the recipes below for anything they cannot do (batches, salt removal, rules, matrices, substructures).

---

## 1. Ready-made functions

```python
from utils.tools.chemistry import resolve_smiles, get_properties, compute_similarity

res = resolve_smiles.invoke({"identifier": "Erlotinib"})     # name, PubChem CID, ChEMBL ID, CAS or InChIKey
# -> {'identifier': 'Erlotinib', 'SMILES': '...'}  or  {'identifier': ..., 'error': '...'}

props = get_properties.invoke({"smiles": "CC(=O)Oc1ccccc1C(=O)O"})
# -> {'SMILES': ..., 'Properties': {'Molecular_Weight', 'LogP', 'HBD', 'HBA', 'TPSA',
#                                   'Rotatable_Bonds', 'Aromatic_Rings', 'Heavy_Atoms', 'Formal_Charge'}}

sim = compute_similarity.invoke({"reference_smiles": ref_smiles, "candidate_smiles": [smiles_a, smiles_b]})
# -> {'ranking': [{'SMILES': ..., 'tanimoto': 0.4}, ...], 'invalid_smiles': [...], ...}
```

Always check for an `'error'` key before using a result.

---

## 2. Remove salts BEFORE computing properties (important)

`resolve_smiles` sometimes returns a salt form, e.g. Erlotinib → `[H+].[Cl-].COCCOc1cc2ncnc(...)`. The counter-ions distort LogP and other descriptors (erlotinib HCl: LogP 0.5 instead of 3.4). Keep the parent molecule:

```python
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

def parent_smiles(smiles: str) -> str:
    """Largest neutral fragment of a SMILES string (removes salts and counter-ions)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    parent = rdMolStandardize.LargestFragmentChooser().choose(mol)
    parent = rdMolStandardize.Uncharger().uncharge(parent)
    return Chem.MolToSmiles(parent)
```

---

## 3. Many compounds → one table, with drug-likeness rules

Lipinski's Rule of Five: MW ≤ 500, LogP ≤ 5, HBD ≤ 5, HBA ≤ 10. A compound **passes if it has at most one violation** (Lipinski et al., 1997). Veber's rules for oral bioavailability: TPSA ≤ 140 Å² and rotatable bonds ≤ 10.

```python
import pandas as pd

def drug_likeness(p: dict) -> dict:
    violations = [rule for rule, broken in {
        "MW > 500": p["Molecular_Weight"] > 500,
        "LogP > 5": p["LogP"] > 5,
        "HBD > 5": p["HBD"] > 5,
        "HBA > 10": p["HBA"] > 10,
    }.items() if broken]
    return {
        "RO5_violations": ", ".join(violations) or "none",
        "passes_lipinski": len(violations) <= 1,
        "passes_veber": p["TPSA"] <= 140 and p["Rotatable_Bonds"] <= 10,
    }

rows = []
for name in ["Erlotinib", "Gefitinib", "Imatinib"]:
    res = resolve_smiles.invoke({"identifier": name})
    if "error" in res:
        rows.append({"compound": name, "error": res["error"]})
        continue
    smiles = parent_smiles(res["SMILES"])
    p = get_properties.invoke({"smiles": smiles})["Properties"]
    rows.append({"compound": name, "SMILES": smiles, **p, **drug_likeness(p)})

df = pd.DataFrame(rows)
df[["compound", "Molecular_Weight", "LogP", "HBD", "HBA", "TPSA", "RO5_violations", "passes_lipinski", "passes_veber"]].round(2)
```

---

## 4. Similarity matrix (all against all)

Same fingerprint as `compute_similarity` (Morgan, radius 2, 2048 bits ≈ ECFP4), so scores are comparable.

```python
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator

generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
valid = df.dropna(subset=["SMILES"])
fps = [generator.GetFingerprint(Chem.MolFromSmiles(s)) for s in valid["SMILES"]]
similarity = pd.DataFrame(
    [DataStructs.BulkTanimotoSimilarity(fp, fps) for fp in fps],
    index=valid["compound"], columns=valid["compound"],
).round(2)
similarity
```

Rule of thumb for this fingerprint: ≥ 0.7 close analogues, 0.4–0.7 related scaffolds, < 0.4 structurally different. To plot the matrix as a heatmap, use the `data_visualization` skill.

---

## 5. Substructure search (does a molecule contain a given core?)

Write the core as SMARTS and test each molecule. Example: the 4-anilinoquinazoline core of EGFR inhibitors such as erlotinib and gefitinib.

```python
core = Chem.MolFromSmarts("c1ccc2ncnc(Nc3ccccc3)c2c1")
valid = valid.assign(has_core=[Chem.MolFromSmiles(s).HasSubstructMatch(core) for s in valid["SMILES"]])
valid[["compound", "has_core"]]
```

---

## Pitfalls

- Never type SMILES from memory: resolve them with `resolve_smiles` and report the ones that fail.
- Run `parent_smiles` before computing properties or similarity.
- LogP here is RDKit's Crippen estimate (calculated, not measured); say so when you report it.
