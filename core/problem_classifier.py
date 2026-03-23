"""
Problem Classifier: Automatic detection of physics problem domains
and selection of appropriate engines / verification strategies.

This module inspects a problem definition dict and returns a structured
ProblemProfile that tells the Orchestrator which engines to activate,
which verification strategy to use, and which physics audits apply.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set

# ---------------------------------------------------------------------------
# Domain taxonomy
# ---------------------------------------------------------------------------

class Domain:
    """Enumeration of recognised physics / maths problem domains."""
    INTEGRAL       = "integral"           # Pure mathematical integral
    GREEN_FUNC     = "greens_function"    # Green's function / DOS derivation
    MANY_BODY      = "many_body"          # Finite‑temperature many‑body (Matsubara, Feynman)
    RG             = "renormalization"    # Renormalization Group flow
    TOPOLOGY       = "topology"           # Berry phase / Chern number
    TRANSPORT      = "transport"          # Kubo formula / conductivity
    OPERATOR_ALG   = "operator_algebra"   # Commutator / anti‑commutator algebra
    UNKNOWN        = "unknown"


class VerifyStrategy:
    """How the Orchestrator should validate each derivation step."""
    NUMERICAL_ORACLE = "numerical_oracle"   # Direct numerical comparison
    PHYSICS_AUDIT    = "physics_audit"      # Causality / sum‑rule / spectral checks
    HYBRID           = "hybrid"             # Oracle where possible + physics audit


class Engine:
    """Names of optional symbolic engines that can be activated."""
    MATSUBARA  = "matsubara_engine"
    FEYNMAN    = "feynman_translator"
    RG         = "rg_operator"


# ---------------------------------------------------------------------------
# ProblemProfile – the classifier output
# ---------------------------------------------------------------------------

@dataclass
class ProblemProfile:
    """Structured description returned by the classifier."""
    domains: List[str]                         # Ordered list of detected domains
    primary_domain: str = Domain.UNKNOWN       # Most specific / dominant domain
    engines: List[str] = field(default_factory=list)  # Engines to instantiate
    verify_strategy: str = VerifyStrategy.NUMERICAL_ORACLE
    physics_audits: List[str] = field(default_factory=list)
    cmp_mode: bool = False                     # Condensed‑matter physics mode
    summary: str = ""                          # Human‑readable one‑liner


# ---------------------------------------------------------------------------
# Keyword / heuristic tables
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS = {
    Domain.GREEN_FUNC: [
        "green", "dos", "density of states", "spectral", "tight-binding",
        "lattice", "band structure", "dispersion",
    ],
    Domain.MANY_BODY: [
        "matsubara", "finite temperature", "self-energy", "self energy",
        "feynman", "diagram", "gap equation", "hartree", "fock",
        "dyson", "bethe-salpeter", "bcs", "superconduc",
    ],
    Domain.RG: [
        "renormalization", "rg flow", "beta function", "scaling dimension",
        "wilsonian", "mode elimination", "cutoff", "running coupling",
    ],
    Domain.TOPOLOGY: [
        "berry", "chern", "topolog", "winding number", "edge state",
        "bulk-boundary", "quantum hall",
    ],
    Domain.TRANSPORT: [
        "kubo", "conductiv", "hall coefficient", "linear response",
        "transport", "drude",
    ],
    Domain.OPERATOR_ALG: [
        "commutator", "anti-commutator", "anticommutator",
        "operator algebra", "pauli", "spinor", "schrieffer-wolff",
        "second quantiz", "creation", "annihilation",
    ],
    Domain.INTEGRAL: [
        "integral", "integrand", "antiderivative", "contour",
    ],
}

_DOMAIN_TO_ENGINES = {
    Domain.MANY_BODY:  [Engine.MATSUBARA, Engine.FEYNMAN],
    Domain.RG:         [Engine.RG],
    Domain.GREEN_FUNC: [Engine.MATSUBARA],   # Often needs analytic continuation
}

_CMP_DOMAINS = {
    Domain.GREEN_FUNC, Domain.MANY_BODY, Domain.RG,
    Domain.TOPOLOGY, Domain.TRANSPORT, Domain.OPERATOR_ALG,
}


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_problem(problem: dict) -> ProblemProfile:
    """
    Inspect a problem definition dict and return a ProblemProfile.

    The classifier examines the following fields (all optional):
        name, target, hint, hamiltonian, integrand, parameters
    """
    # Concatenate all textual fields into a single searchable blob
    blob_parts = []
    for key in ("name", "target", "hint", "hamiltonian", "integrand", "description"):
        val = problem.get(key, "")
        if val:
            blob_parts.append(str(val))
    blob = " ".join(blob_parts).lower()

    # Score each domain
    domain_scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in blob)
        if score > 0:
            domain_scores[domain] = score

    # Fallback: if nothing matched, label as INTEGRAL if 'integrand' key exists
    if not domain_scores:
        if "integrand" in problem:
            domain_scores[Domain.INTEGRAL] = 1
        else:
            return ProblemProfile(
                domains=[Domain.UNKNOWN],
                primary_domain=Domain.UNKNOWN,
                verify_strategy=VerifyStrategy.NUMERICAL_ORACLE,
                summary="Could not classify problem; defaulting to generic solver.",
            )

    # Sort by score descending
    sorted_domains = sorted(domain_scores, key=lambda d: domain_scores[d], reverse=True)
    primary = sorted_domains[0]

    # Collect engines
    engines: List[str] = []
    seen_engines: Set[str] = set()
    for d in sorted_domains:
        for eng in _DOMAIN_TO_ENGINES.get(d, []):
            if eng not in seen_engines:
                engines.append(eng)
                seen_engines.add(eng)

    # Determine verification strategy
    cmp_mode = any(d in _CMP_DOMAINS for d in sorted_domains)
    if cmp_mode and Domain.INTEGRAL in sorted_domains:
        verify_strategy = VerifyStrategy.HYBRID
    elif cmp_mode:
        verify_strategy = VerifyStrategy.PHYSICS_AUDIT
    else:
        verify_strategy = VerifyStrategy.NUMERICAL_ORACLE

    # Physics audits
    audits: List[str] = []
    if cmp_mode:
        audits.append("causality")
        audits.append("spectral_positivity")
        audits.append("sum_rule")
        audits.append("conservation")

    summary_parts = [f"Detected domains: {', '.join(sorted_domains)}"]
    if engines:
        summary_parts.append(f"Engines: {', '.join(engines)}")
    summary_parts.append(f"Verification: {verify_strategy}")

    return ProblemProfile(
        domains=sorted_domains,
        primary_domain=primary,
        engines=engines,
        verify_strategy=verify_strategy,
        physics_audits=audits,
        cmp_mode=cmp_mode,
        summary=" | ".join(summary_parts),
    )
