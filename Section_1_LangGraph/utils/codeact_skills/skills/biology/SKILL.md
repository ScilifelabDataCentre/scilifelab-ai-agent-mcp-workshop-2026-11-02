---
name: biology
description: Proteins, drug targets and peptides. Look up protein function, location and diseases (UniProt), a drug's targets, mechanism of action and indications (ChEMBL), protein interaction partners (STRING), fetch protein sequences, compute sequence properties and align sequences (Biopython). Use for any question about targets, mechanisms, protein biology or protein/peptide sequences.
---

# Biology (targets, proteins, sequences)

This skill wraps the **same functions as the ReAct agent's biology tools** (`utils/tools/biology.py`), so both agents give consistent answers. Use the ready-made functions first; use the recipes below for batches, comparisons, full sequences and alignments.

---

## 1. Ready-made functions

```python
from utils.tools.biology import get_protein_info, get_drug_targets, get_protein_interactions, analyze_protein_sequence

get_protein_info.invoke({"gene_symbol": "ABL1"})                     # organism: "human" (default), "mouse" or "rat"
# -> {'uniprot_accession', 'protein_name', 'length_aa', 'function', 'subcellular_location', 'associated_diseases'}

get_drug_targets.invoke({"drug_name": "Imatinib"})                   # generic or brand name
# -> {'chembl_id', 'preferred_name', 'max_clinical_phase',
#     'mechanisms': [{'mechanism_of_action', 'action_type', 'target': {'name', 'type', 'gene_symbols'}}],
#     'indications': [{'disease', 'max_phase'}]}

get_protein_interactions.invoke({"gene_symbol": "EGFR", "limit": 10})
# -> {'interaction_partners': [{'partner', 'confidence', 'experimental_evidence', 'curated_databases'}]}

analyze_protein_sequence.invoke({"sequence": "HAEGTFTSDVSSYLEGQAAKEFIAWLVKGRG"})
# -> {'length_aa', 'molecular_weight_da', 'isoelectric_point', 'net_charge_at_pH_7.4', 'gravy',
#     'instability_index', 'predicted_stable_in_vitro', ...}
```

Always check for an `'error'` key. Use **official gene symbols** (ABL1, not "BCR-ABL" or "c-Abl"). If `mechanisms` has no annotation it is a string, not a list.

---

## 2. Targets of several drugs → shared and unique targets

```python
import pandas as pd

def target_genes(drug: str) -> set[str]:
    res = get_drug_targets.invoke({"drug_name": drug})
    if "error" in res or not isinstance(res["mechanisms"], list):
        print(f"{drug}: {res.get('error', 'no mechanism annotated')}")
        return set()
    return {gene for m in res["mechanisms"] for gene in m["target"].get("gene_symbols", [])}

targets = {drug: target_genes(drug) for drug in ["Imatinib", "Dasatinib", "Nilotinib"]}
shared = set.intersection(*targets.values())
print("Shared targets:", shared)
pd.DataFrame({drug: {g: g in genes for g in set().union(*targets.values())} for drug, genes in targets.items()})
```

---

## 3. Fetch a full protein sequence (UniProt)

`get_protein_info` does not return the sequence (to keep the LLM context small). Fetch it when you need to compute on it, and **do not print whole sequences**: print the length and a short preview.

```python
import requests

def fetch_sequence(uniprot_accession: str) -> str:
    response = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_accession}.fasta", timeout=30)
    response.raise_for_status()
    return "".join(response.text.splitlines()[1:])   # drop the FASTA header line

accession = get_protein_info.invoke({"gene_symbol": "EGFR"})["uniprot_accession"]
egfr = fetch_sequence(accession)
print(len(egfr), egfr[:60] + "...")
```

---

## 4. Sequence properties at other conditions

`analyze_protein_sequence` reports charge at pH 7.4. For other questions use Biopython directly:

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis

analysis = ProteinAnalysis("HAEGTFTSDVSSYLEGQAAKEFIAWLVKGRG")
{pH: round(analysis.charge_at_pH(pH), 2) for pH in [2.0, 5.0, 7.4, 9.0]}   # e.g. stomach vs blood
```

---

## 5. Align two sequences (identity, differences)

```python
from Bio import Align
from Bio.Align import substitution_matrices

def align(seq_a: str, seq_b: str):
    aligner = Align.PairwiseAligner(
        mode="global",
        substitution_matrix=substitution_matrices.load("BLOSUM62"),
        open_gap_score=-10, extend_gap_score=-0.5,
    )
    alignment = aligner.align(seq_a, seq_b)[0]
    counts = alignment.counts()
    identity = counts.identities / min(len(seq_a), len(seq_b))
    return alignment, round(100 * identity, 1)

alignment, identity_pct = align("HAEGTFTSDVSSYLEGQAAKEFIAWLVKGRG", "HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS")
print(alignment)
print(f"Identity: {identity_pct}% of the shorter sequence")
```

Positions where the sequences differ often explain differences in stability or activity (e.g. residue 2 of GLP-1 analogues and DPP-4 cleavage).

---

## 6. Compare interaction networks

```python
def partners(gene: str, n: int = 50) -> dict[str, float]:
    res = get_protein_interactions.invoke({"gene_symbol": gene, "limit": n})
    return {p["partner"]: p["confidence"] for p in res.get("interaction_partners", [])}

egfr, erbb2 = partners("EGFR"), partners("ERBB2")
common = sorted(egfr.keys() & erbb2.keys(), key=lambda g: -min(egfr[g], erbb2[g]))
print(f"{len(common)} common partners:", common[:15])
```

STRING confidence: ≥ 0.7 high, ≥ 0.9 highest. `experimental_evidence` shows how much of it comes from lab experiments.

---

## Pitfalls

- Gene symbols are case-sensitive per organism: human `EGFR`, mouse `Egfr`.
- ChEMBL mechanisms describe the **intended** targets of approved/clinical drugs, not every off-target.
- Sequence-based predictions (instability index, GRAVY) ignore modifications (amidation, lipidation, PEGylation) and in vivo processes such as enzymatic cleavage or renal clearance. Back up claims about in vivo behaviour with the `literature` skill.
