"""
Integration test for the Orchestrator's routing logic.

Uses unittest.mock to simulate LLM (Theorist/Coder/Verifier) responses,
proving that the auto-routing pipeline correctly:
  1. Classifies the problem
  2. Loads the right engines
  3. Dispatches verification to the right strategy
  4. Passes engine context to the Theorist
  5. Handles terminal steps through Coder → Verifier chain

This test does NOT require an API key.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from unittest.mock import patch, MagicMock

from core.problem_classifier import classify_problem, Domain, Engine, VerifyStrategy
from core.orchestrator import ResearchOrchestrator


# ─── Mock LLM Responses ────────────────────────────────────────

MOCK_THEORIST_PROPOSALS = [
    {
        "action_type": "Fourier Transform to k-space",
        "logic": "Transform real-space Hamiltonian H = -t sum c†_i c_j to k-space: epsilon(k) = -2t cos(k)",
        "intermediate_expression": "\\epsilon(k) = -2t \\cos(k)",
        "sympy_code": "-2*t*cos(k)",
        "is_terminal": False,
        "success_probability": 0.95,
        "simplicity_score": 9,
    },
    {
        "action_type": "Construct Green's Function",
        "logic": "Build retarded Green's function G(k,w) = 1/(w - epsilon(k) + i*eta)",
        "intermediate_expression": "G(k,\\omega) = \\frac{1}{\\omega + 2t\\cos(k) + i\\eta}",
        "sympy_code": "1/(omega + 2*t*cos(k) + I*eta)",
        "is_terminal": False,
        "success_probability": 0.90,
        "simplicity_score": 8,
    },
    {
        "action_type": "Compute DOS via Im[G]",
        "logic": "D(omega) = -1/pi Im integral G dk",
        "intermediate_expression": "D(\\omega) = \\frac{1}{\\pi\\sqrt{4t^2 - \\omega^2}}",
        "sympy_code": "1/(pi*sqrt(4*t**2 - omega**2))",
        "is_terminal": True,
        "success_probability": 0.85,
        "simplicity_score": 10,
    },
]


# ─── Tests ──────────────────────────────────────────────────────

class TestOrchestratorRouting:
    """Test the auto-routing logic without making any API calls."""

    def test_cmp_problem_activates_physics_audit(self):
        """CMP problem → physics_audit strategy + Matsubara engine."""
        problem = {
            "name": "1D Tight-Binding DOS Derivation",
            "hamiltonian": "H = -t Sum c†_i c_j",
            "integrand": "SpectralFunction(k, omega)",
            "target": "Density of States",
            "hint": "Green's function, spectral, lattice",
            "parameters": ["t=1.0", "eta=0.01"],
        }

        # Patch the LLM agents so they don't need API keys
        with patch('core.orchestrator.TheoristAgent') as MockTheorist, \
             patch('core.orchestrator.CoderAgent') as MockCoder, \
             patch('core.orchestrator.VerifierAgent') as MockVerifier, \
             patch('core.orchestrator.ReporterAgent') as MockReporter:

            orch = ResearchOrchestrator(problem)

            # Verify classification
            assert orch.profile.cmp_mode is True
            assert orch.profile.verify_strategy in (
                VerifyStrategy.PHYSICS_AUDIT, VerifyStrategy.HYBRID
            )
            assert Engine.MATSUBARA in orch.profile.engines
            assert "causality" in orch.profile.physics_audits

            print("  [PASS] CMP routing: physics_audit + Matsubara ✓")

    def test_integral_problem_uses_oracle(self):
        """Pure integral → numerical_oracle strategy, no engines."""
        problem = {
            "name": "Parametric Integral",
            "integrand": "sin(a*x)/(x*(x**2+1))",
            "bounds": "[0, oo]",
            "parameters": ["a=1"],
            "target": "Evaluate integral",
        }

        with patch('core.orchestrator.TheoristAgent'), \
             patch('core.orchestrator.CoderAgent'), \
             patch('core.orchestrator.VerifierAgent'), \
             patch('core.orchestrator.ReporterAgent'):

            orch = ResearchOrchestrator(problem)

            assert orch.profile.cmp_mode is False
            assert orch.profile.verify_strategy == VerifyStrategy.NUMERICAL_ORACLE
            assert len(orch.profile.engines) == 0

            print("  [PASS] Integral routing: oracle, no engines ✓")

    def test_context_includes_active_engines(self):
        """Verify that the distilled context passed to Theorist includes engine info."""
        problem = {
            "name": "BCS Gap Equation",
            "target": "Derive gap equation using Feynman diagram and Matsubara sum",
            "hint": "self-energy, finite temperature",
            "parameters": ["V=0.5"],
        }

        with patch('core.orchestrator.TheoristAgent'), \
             patch('core.orchestrator.CoderAgent'), \
             patch('core.orchestrator.VerifierAgent'), \
             patch('core.orchestrator.ReporterAgent'):

            orch = ResearchOrchestrator(problem)

            dummy_node = {"path": [], "expression": "H"}
            ctx = orch._distill_context(dummy_node)

            assert "active_engines" in ctx
            assert "problem_profile" in ctx
            assert Engine.MATSUBARA in ctx["active_engines"]
            assert Engine.FEYNMAN in ctx["active_engines"]
            assert ctx["problem_profile"]["primary_domain"] == Domain.MANY_BODY

            print("  [PASS] Theorist context includes engines & profile ✓")

    def test_full_search_loop_with_mock_llm(self):
        """
        Simulate a COMPLETE search loop:
          Theorist proposes 3 steps → Physics Audit validates → Terminal → Coder → Verifier
        This proves the LLM agents are wired into the pipeline correctly.
        """
        problem = {
            "name": "1D Tight-Binding DOS Derivation",
            "hamiltonian": "H = -t Sum c†_i c_j",
            "integrand": "SpectralFunction(k, omega)",
            "target": "Density of States D(omega)",
            "hint": "Green's function, spectral",
            "parameters": ["t=1.0", "eta=0.01"],
        }

        with patch('core.orchestrator.TheoristAgent') as MockTheoristCls, \
             patch('core.orchestrator.CoderAgent') as MockCoderCls, \
             patch('core.orchestrator.VerifierAgent') as MockVerifierCls, \
             patch('core.orchestrator.ReporterAgent') as MockReporterCls:

            # Configure mock Theorist: returns our 3 proposals
            mock_theorist = MockTheoristCls.return_value
            mock_theorist.solve.return_value = MOCK_THEORIST_PROPOSALS

            # Configure mock Coder: returns a dummy script
            mock_coder = MockCoderCls.return_value
            mock_coder.generate_implementation.return_value = {
                "python_script": "print(0.15915494309189535)"  # 1/(2*pi)
            }

            # Configure mock Verifier: returns SUCCESS
            mock_verifier = MockVerifierCls.return_value
            mock_verifier.verify.return_value = {
                "status": "SUCCESS",
                "residual": 1e-15,
            }

            # Configure mock Reporter
            mock_reporter = MockReporterCls.return_value
            mock_reporter.generate_report.return_value = "mock_report.md"

            orch = ResearchOrchestrator(problem, report_language="English")
            orch.run()

            # ── Assert the full pipeline was exercised ──

            # 1. Theorist was called (LLM thinking step)
            assert mock_theorist.solve.called, "Theorist.solve() was never called!"
            call_args = mock_theorist.solve.call_args
            # The context should include active_engines
            ctx_passed = call_args[1].get('context') or call_args[0][1]
            assert "active_engines" in ctx_passed

            # 2. Coder was called for the terminal step
            assert mock_coder.generate_implementation.called, \
                "Coder.generate_implementation() was never called!"

            # 3. Verifier was called
            assert mock_verifier.verify.called, \
                "Verifier.verify() was never called!"

            # 4. Reporter was called on success
            assert mock_reporter.generate_report.called, \
                "Reporter.generate_report() was never called!"

            print("  [PASS] Full loop: Theorist → Audit → Coder → Verifier → Reporter ✓")


if __name__ == "__main__":
    print("=" * 64)
    print("  Integration Tests: Orchestrator LLM Routing (Mock Mode)")
    print("=" * 64)

    t = TestOrchestratorRouting()
    t.test_cmp_problem_activates_physics_audit()
    t.test_integral_problem_uses_oracle()
    t.test_context_includes_active_engines()
    t.test_full_search_loop_with_mock_llm()

    print("\n  All integration tests passed! ✓")
