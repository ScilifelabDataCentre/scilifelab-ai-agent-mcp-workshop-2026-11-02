"""
Ready-made biology tools for the drug discovery agent in Part 2 of the LangGraph workshop.

- get_protein_info:         gene symbol -> protein function, subcellular location, diseases (UniProt)
- get_drug_targets:         drug name -> molecular targets, mechanism of action, indications (ChEMBL)
- get_protein_interactions: gene symbol -> strongest protein-protein interaction partners (STRING)
- analyze_protein_sequence: amino acid sequence -> mass, pI, charge, hydrophobicity, stability (Biopython)
"""

from typing import Literal

import requests
from Bio.SeqUtils.ProtParam import ProteinAnalysis
from langchain.tools import tool


UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
STRING_API = "https://string-db.org/api/json"

# Internal settings: kept out of the tool signatures, so the LLM never sees (or tries to set) them
REQUEST_TIMEOUT_S = 30.0
MAX_TEXT_CHARS = 1500
TAXON_IDS = {"human": 9606, "mouse": 10090, "rat": 10116}
AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")
PHYSIOLOGICAL_PH = 7.4


# Helper functions
def _get_json(url: str, params: dict) -> dict:
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    return response.json()

def _shorten(text: str) -> str:
    return text if len(text) <= MAX_TEXT_CHARS else text[:MAX_TEXT_CHARS] + " [...]"


# Tool 1: PROTEIN INFO
@tool(parse_docstring=True)
def get_protein_info(gene_symbol: str, organism: Literal["human", "mouse", "rat"] = "human") -> dict:
    """Look up a protein in UniProt: its function, where it is located in the cell, and the diseases it is involved in.

    Args:
        gene_symbol: Official gene symbol of the protein, e.g. EGFR, ABL1 or TP53.
        organism: Organism the protein comes from.

    Returns:
        UniProt accession, protein name, function, subcellular locations and associated diseases, or an error message.
    """
    query = f"gene_exact:{gene_symbol.strip()} AND organism_id:{TAXON_IDS[organism]} AND reviewed:true"
    fields = "accession,protein_name,gene_primary,length,cc_function,cc_subcellular_location,cc_disease"
    try:
        data = _get_json(UNIPROT_SEARCH, {"query": query, "fields": fields, "format": "json", "size": 1})
    except requests.RequestException as e:
        return {'gene_symbol': gene_symbol, 'error': f'UniProt request failed ({e}). Try again later.'}

    if not data.get("results"):
        return {
            'gene_symbol': gene_symbol,
            'error': f'No reviewed {organism} UniProt entry found. Check that this is an official gene symbol (e.g. ABL1, not BCR-ABL).',
        }

    entry = data["results"][0]
    function, locations, diseases = [], [], []
    for comment in entry.get("comments", []):
        kind = comment.get("commentType")
        if kind == "FUNCTION":
            function += [t["value"] for t in comment.get("texts", [])]
        elif kind == "SUBCELLULAR LOCATION":
            locations += [loc["location"]["value"] for loc in comment.get("subcellularLocations", [])]
        elif kind == "DISEASE" and "disease" in comment:
            diseases.append(comment["disease"]["diseaseId"])

    return {
        'gene_symbol': gene_symbol,
        'uniprot_accession': entry["primaryAccession"],
        'protein_name': entry["proteinDescription"]["recommendedName"]["fullName"]["value"],
        'length_aa': entry["sequence"]["length"] if "sequence" in entry else None,
        'function': _shorten(" ".join(function)) or "Not annotated.",
        'subcellular_location': sorted(set(locations)),
        'associated_diseases': diseases,
    }


# Tool 2: DRUG TARGETS
@tool(parse_docstring=True)
def get_drug_targets(drug_name: str) -> dict:
    """Find the molecular targets and mechanism of action of a drug, and the diseases it is used for (ChEMBL).

    Args:
        drug_name: Name of the drug, e.g. Imatinib or Gefitinib (brand names also work).

    Returns:
        ChEMBL ID, highest clinical phase, mechanisms of action with their targets, and indications, or an error message.
    """
    try:
        hits = _get_json(f"{CHEMBL_API}/molecule/search.json", {"q": drug_name.strip(), "limit": 5})["molecules"]
        if not hits:
            return {'drug_name': drug_name, 'error': 'Drug not found in ChEMBL. Try another name (e.g. generic name).'}

        # Mechanisms are stored for the parent compound, not for its salts (e.g. imatinib mesylate -> imatinib)
        parent_id = (hits[0].get("molecule_hierarchy") or {}).get("parent_chembl_id") or hits[0]["molecule_chembl_id"]
        parent = _get_json(f"{CHEMBL_API}/molecule/{parent_id}.json", {})

        mechanisms = _get_json(f"{CHEMBL_API}/mechanism.json", {"parent_molecule_chembl_id": parent_id, "limit": 20})["mechanisms"]
        target_ids = sorted({m["target_chembl_id"] for m in mechanisms if m.get("target_chembl_id")})
        targets = {}
        if target_ids:
            for t in _get_json(f"{CHEMBL_API}/target.json", {"target_chembl_id__in": ",".join(target_ids), "limit": 20})["targets"]:
                genes = {
                    syn["component_synonym"]
                    for comp in t.get("target_components", [])
                    for syn in comp.get("target_component_synonyms", [])
                    if syn.get("syn_type") == "GENE_SYMBOL"
                }
                targets[t["target_chembl_id"]] = {'name': t["pref_name"], 'type': t["target_type"], 'gene_symbols': sorted(genes)}

        indications = _get_json(
            f"{CHEMBL_API}/drug_indication.json",
            {"parent_molecule_chembl_id": parent_id, "order_by": "-max_phase_for_ind", "limit": 10},
        )["drug_indications"]
    except (requests.RequestException, KeyError) as e:
        return {'drug_name': drug_name, 'error': f'ChEMBL request failed ({e}). Try again later.'}

    # The same disease can be listed several times; indications are sorted by phase, so keep the first (highest)
    indication_phases = {}
    for ind in indications:
        indication_phases.setdefault(ind["efo_term"] or ind["mesh_heading"], ind["max_phase_for_ind"])

    return {
        'drug_name': drug_name,
        'chembl_id': parent_id,
        'preferred_name': parent.get("pref_name"),
        'max_clinical_phase': parent.get("max_phase"),
        'mechanisms': [
            {
                'mechanism_of_action': m["mechanism_of_action"],
                'action_type': m["action_type"],
                'target': targets.get(m["target_chembl_id"], {'name': m["target_chembl_id"]}),
            }
            for m in mechanisms
        ] or 'No mechanism of action annotated in ChEMBL.',
        'indications': [{'disease': disease, 'max_phase': phase} for disease, phase in indication_phases.items()],
    }


# Tool 3: PROTEIN-PROTEIN INTERACTIONS
@tool(parse_docstring=True)
def get_protein_interactions(gene_symbol: str, limit: int = 10, organism: Literal["human", "mouse", "rat"] = "human") -> dict:
    """Find the strongest known interaction partners of a protein in the STRING database.

    Args:
        gene_symbol: Official gene symbol of the protein, e.g. EGFR, ABL1 or TP53.
        limit: Maximum number of interaction partners to return (default is 10).
        organism: Organism the protein comes from.

    Returns:
        Interaction partners sorted by STRING confidence score (0-1, above 0.7 is high confidence), or an error message.
    """
    params = {
        "identifiers": gene_symbol.strip(),
        "species": TAXON_IDS[organism],
        "limit": limit,
        "caller_identity": "scilifelab_langgraph_workshop",
    }
    try:
        partners = _get_json(f"{STRING_API}/interaction_partners", params)
    except requests.RequestException as e:
        return {'gene_symbol': gene_symbol, 'error': f'STRING request failed or protein not found ({e}). Check the gene symbol.'}

    if not partners:
        return {'gene_symbol': gene_symbol, 'error': 'No interaction partners found. Check the gene symbol.'}

    return {
        'gene_symbol': gene_symbol,
        'interaction_partners': [
            {
                'partner': p["preferredName_B"],
                'confidence': p["score"],
                'experimental_evidence': p["escore"],   # part of the score backed by lab experiments
                'curated_databases': p["dscore"],       # part of the score backed by pathway databases
            }
            for p in sorted(partners, key=lambda p: p["score"], reverse=True)
        ],
    }


# Tool 4: PROTEIN / PEPTIDE SEQUENCE ANALYSIS
@tool(parse_docstring=True)
def analyze_protein_sequence(sequence: str) -> dict:
    """Calculate physicochemical properties of a protein or peptide from its amino acid sequence.

    Args:
        sequence: Amino acid sequence in one-letter code, e.g. HAEGTFTSDVSSYLEGQAAKEFIAWLVKGRG.

    Returns:
        Length, molecular weight, isoelectric point, net charge at pH 7.4, hydrophobicity (GRAVY), instability index, extinction coefficient and amino acid composition, or an error message.
    """
    seq = "".join(sequence.split()).upper()   # tolerate spaces and line breaks
    unknown = sorted(set(seq) - AMINO_ACIDS)
    if not seq or unknown:
        return {'error': f"Sequence must use the 20 standard one-letter amino acid codes. Unknown characters: {unknown or 'empty sequence'}."}

    analysis = ProteinAnalysis(seq)
    instability = analysis.instability_index()
    composition = sorted(analysis.amino_acids_percent.items(), key=lambda item: item[1], reverse=True)
    ext_reduced, ext_disulfide = analysis.molar_extinction_coefficient()

    return {
        'length_aa': len(seq),
        'molecular_weight_da': round(analysis.molecular_weight(), 1),
        'isoelectric_point': round(analysis.isoelectric_point(), 2),
        'net_charge_at_pH_7.4': round(analysis.charge_at_pH(PHYSIOLOGICAL_PH), 2),
        'gravy': round(analysis.gravy(), 3),   # grand average of hydropathy: > 0 hydrophobic, < 0 hydrophilic
        'instability_index': round(instability, 1),
        'predicted_stable_in_vitro': instability < 40,   # Guruprasad et al. 1990: < 40 means stable
        'aromaticity': round(analysis.aromaticity(), 3),
        'extinction_coefficient_280nm': {'cysteines_reduced': ext_reduced, 'disulfide_bonds': ext_disulfide},
        'most_abundant_amino_acids_percent': {aa: round(pct, 1) for aa, pct in composition[:5]},
        'note': 'Computed for the linear sequence only: modifications (amidation, lipidation, PEGylation, ...) are not taken into account.',
    }
