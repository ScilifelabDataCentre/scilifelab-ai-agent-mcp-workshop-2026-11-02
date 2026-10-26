"""
Ready-made chemistry tools for the drug discovery agent in Part 2 of the LangGraph workshop.

- resolve_smiles: any compound identifier (name, PubChem CID, ChEMBL ID, CAS, InChIKey) -> SMILES
- get_properties: SMILES -> basic physicochemical properties (RDKit)
- compute_similarity: reference SMILES + candidate SMILES -> structural similarity (RDKit fingerprints)
"""

import re
import time
from urllib.parse import quote

import requests
import pubchempy as pcp
from chembl_webresource_client.new_client import new_client
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, rdFingerprintGenerator
from langchain.tools import tool


# Tool 1: SMILES RESOLVER
CACTUS_BASE = "https://cactus.nci.nih.gov/chemical/structure"
molecule = new_client.molecule

# Internal settings: kept out of the tool signature, so the LLM never sees (or tries to set) them
REQUEST_TIMEOUT_S = 15.0
PAUSE_S = 0.0


# Helper functions
def _is_chembl_id(value: str) -> bool:
    return bool(re.fullmatch(r"CHEMBL\d+", value.upper()))

def _looks_like_inchikey(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", value))


@tool(parse_docstring=True)
def resolve_smiles(identifier: str) -> dict:
    """Resolve any compound identifier to a canonical SMILES string.

    Args:
        identifier: Any identifier of a compound, e.g. name, PubChem CID, ChEMBL ID, CAS number or InChIKey.

    Returns:
        The original identifier with its SMILES string, or an error message if it could not be resolved.
    """
    ident = identifier.strip()
    if not ident:
        return {'identifier': identifier, 'error': 'Empty identifier.'}

    ident_lower = ident.lower()
    ident_upper = ident.upper()

    # Try ChEMBL first if it looks like a ChEMBL ID
    if _is_chembl_id(ident_upper):
        try:
            mol = molecule.get(ident_upper)
            smiles = mol.get("molecule_structures", {}).get("canonical_smiles")
            if smiles:
                if PAUSE_S:
                    time.sleep(PAUSE_S)
                return {'identifier': identifier, 'SMILES': smiles}
        except Exception:
            pass

    # Try CACTUS
    try:
        url = f"{CACTUS_BASE}/{quote(ident)}/smiles"
        response = requests.get(url, timeout=REQUEST_TIMEOUT_S, headers={"User-Agent": "smiles-resolver/1.0"})
        if response.ok:
            text = response.text.strip()
            # Explicitly check for non-empty and valid content
            if (text  and len(text) > 0 ):
                if PAUSE_S:
                    time.sleep(PAUSE_S)
                return {'identifier': identifier, 'SMILES': text}
            # If empty or invalid, fall through to PubChem
    except requests.RequestException:
        pass

    # Try PubChem
    try:
        if ident.isdigit():
            compound = pcp.Compound.from_cid(int(ident))
            smiles = getattr(compound, "canonical_smiles", None)
            if smiles:
                if PAUSE_S:
                    time.sleep(PAUSE_S)
                return {'identifier': identifier, 'SMILES': smiles}

        if _looks_like_inchikey(ident_upper):
            compounds = pcp.get_compounds(ident_upper, namespace="inchikey")
        else:
            compounds = pcp.get_compounds(ident_lower, namespace="name")

        if compounds:
            smiles = getattr(compounds[0], "canonical_smiles", None)
            if smiles:
                if PAUSE_S:
                    time.sleep(PAUSE_S)
                return {'identifier': identifier, 'SMILES': smiles}
    except Exception:
        pass

    # Tell the LLM *why* nothing came back, so it can try another identifier instead of guessing
    return {
        'identifier': identifier,
        'error': 'Could not resolve this identifier in ChEMBL, CACTUS or PubChem. Try another name or identifier.',
    }


# Tool 2: GET PROPERTIES
@tool(parse_docstring=True)
def get_properties(smiles: str) -> dict:
    """Calculate basic molecular properties from a SMILES string.

    Args:
        smiles: SMILES string representation of the molecule

    Returns:
        Dictionary containing molecular properties
    """
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return {"error": "Invalid SMILES string"}


    properties = {
        "Molecular_Weight": Descriptors.MolWt(mol),
        "LogP": Descriptors.MolLogP(mol),
        "HBD": Descriptors.NumHDonors(mol),  # Hydrogen Bond Donors
        "HBA": Descriptors.NumHAcceptors(mol),  # Hydrogen Bond Acceptors
        "TPSA": Descriptors.TPSA(mol),  # Topological Polar Surface Area
        "Rotatable_Bonds": Descriptors.NumRotatableBonds(mol),
        "Aromatic_Rings": Descriptors.NumAromaticRings(mol),
        "Heavy_Atoms": Descriptors.HeavyAtomCount(mol),
        "Formal_Charge": Chem.GetFormalCharge(mol),
    }

    return {
        'SMILES': smiles,
        'Properties': properties
    }


# Tool 3: STRUCTURAL SIMILARITY
# Morgan fingerprint with radius 2 (equivalent to ECFP4), the usual default for similarity searching
MORGAN_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


@tool(parse_docstring=True)
def compute_similarity(reference_smiles: str, candidate_smiles: list[str]) -> dict:
    """Compute how structurally similar candidate molecules are to a reference molecule (Tanimoto similarity of Morgan fingerprints).

    Args:
        reference_smiles: SMILES string of the reference molecule.
        candidate_smiles: SMILES strings of the molecules to compare with the reference.

    Returns:
        Candidates ranked from most to least similar, with a Tanimoto score between 0 (nothing in common) and 1 (identical fingerprints).
    """
    reference = Chem.MolFromSmiles(reference_smiles)
    if reference is None:
        return {"error": "Invalid reference SMILES string"}

    valid, invalid = [], []
    for smiles in candidate_smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            invalid.append(smiles)
        else:
            valid.append((smiles, mol))
    if not valid:
        return {"error": "None of the candidate SMILES strings are valid", "invalid_smiles": invalid}

    scores = DataStructs.BulkTanimotoSimilarity(
        MORGAN_GENERATOR.GetFingerprint(reference),
        [MORGAN_GENERATOR.GetFingerprint(mol) for _, mol in valid],
    )
    ranking = sorted(zip([smiles for smiles, _ in valid], scores), key=lambda pair: pair[1], reverse=True)

    return {
        'reference_SMILES': reference_smiles,
        'fingerprint': 'Morgan, radius 2, 2048 bits (ECFP4-like)',
        'ranking': [{'SMILES': smiles, 'tanimoto': round(score, 3)} for smiles, score in ranking],
        'invalid_smiles': invalid,
        'interpretation': 'As a rule of thumb, Tanimoto >= 0.7: close analogues; 0.4-0.7: related scaffolds; < 0.4: structurally different.',
    }
