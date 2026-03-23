"""
Tests for the ProblemClassifier and the unified ResearchOrchestrator init.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.problem_classifier import (
    classify_problem, Domain, VerifyStrategy, Engine,
)


def test_classify_cmp_dos():
    """A Tight-Binding DOS problem should auto-detect as CMP."""
    problem = {
        "name": "1D Tight-Binding DOS Derivation",
        "hamiltonian": "H = -t * Sum(c_dagger_i * c_j)",
        "integrand": "SpectralFunction(k, omega)",
        "target": "Find the Density of States D(omega)",
        "hint": "Fourier transform to k-space, Green's function, spectral",
    }
    profile = classify_problem(problem)

    assert profile.cmp_mode is True
    assert Domain.GREEN_FUNC in profile.domains
    assert profile.verify_strategy in (VerifyStrategy.PHYSICS_AUDIT, VerifyStrategy.HYBRID)
    assert Engine.MATSUBARA in profile.engines
    print(f"  [PASS] CMP/DOS → {profile.summary}")


def test_classify_many_body():
    """A self-energy / Matsubara problem should activate Feynman + Matsubara."""
    problem = {
        "name": "Finite-Temperature Hartree Self-Energy",
        "target": "Derive the Hartree self-energy at finite temperature using Matsubara formalism",
        "hint": "Feynman diagram, Matsubara sum, self-energy",
    }
    profile = classify_problem(problem)

    assert profile.cmp_mode is True
    assert Domain.MANY_BODY in profile.domains
    assert Engine.MATSUBARA in profile.engines
    assert Engine.FEYNMAN in profile.engines
    print(f"  [PASS] Many-Body → {profile.summary}")


def test_classify_rg():
    """An RG flow problem should activate the RG operator."""
    problem = {
        "name": "Phi-4 Renormalization Group Flow",
        "target": "Derive the beta function for the quartic coupling",
        "hint": "Wilsonian mode elimination, scaling dimension, running coupling",
    }
    profile = classify_problem(problem)

    assert profile.cmp_mode is True
    assert Domain.RG in profile.domains
    assert Engine.RG in profile.engines
    print(f"  [PASS] RG → {profile.summary}")


def test_classify_pure_integral():
    """A pure math integral should use numerical oracle, no engines."""
    problem = {
        "name": "Parametric Sinusoidal Decay Integral",
        "integrand": "sin(a*x) / (x * (x**2 + 1))",
        "bounds": "[0, oo]",
        "parameters": ["a=1"],
        "target": "Evaluate the integral analytically.",
    }
    profile = classify_problem(problem)

    assert profile.cmp_mode is False
    assert Domain.INTEGRAL in profile.domains
    assert profile.verify_strategy == VerifyStrategy.NUMERICAL_ORACLE
    assert len(profile.engines) == 0
    print(f"  [PASS] Integral → {profile.summary}")


def test_classify_topology():
    """A topological problem should flag CMP mode."""
    problem = {
        "name": "Haldane Model Chern Number",
        "target": "Compute the Chern number from Berry curvature",
        "hint": "Berry phase, topological invariant, edge states",
    }
    profile = classify_problem(problem)

    assert profile.cmp_mode is True
    assert Domain.TOPOLOGY in profile.domains
    print(f"  [PASS] Topology → {profile.summary}")


def test_classify_unknown():
    """An empty problem should gracefully return UNKNOWN."""
    profile = classify_problem({"name": "???"})
    assert profile.primary_domain == Domain.UNKNOWN
    print(f"  [PASS] Unknown → {profile.summary}")


if __name__ == "__main__":
    print("="*60)
    print(" ProblemClassifier Unit Tests")
    print("="*60)
    test_classify_cmp_dos()
    test_classify_many_body()
    test_classify_rg()
    test_classify_pure_integral()
    test_classify_topology()
    test_classify_unknown()
    print("\nAll classifier tests passed! ✓")
