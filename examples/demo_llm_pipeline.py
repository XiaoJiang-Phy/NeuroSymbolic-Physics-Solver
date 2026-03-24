"""
╔══════════════════════════════════════════════════════════════════╗
║  End-to-End NeuroSymbolic Solver Demo (REQUIRES API KEY)         ║
║                                                                  ║
║  This is the REAL LLM-powered demo. It calls DeepSeek-R1 for    ║
║  reasoning, DeepSeek-V3 for code generation, and runs the full   ║
║  Orchestrator pipeline:                                          ║
║                                                                  ║
║    Classifier → Theorist(LLM) → PhysicsAudit → Coder(LLM)      ║
║    → Verifier(LLM) → Reporter(LLM)                              ║
║                                                                  ║
║  Usage:                                                          ║
║    python examples/demo_llm_pipeline.py --problem cmp            ║
║    python examples/demo_llm_pipeline.py --problem integral       ║
║                                                                  ║
║  Prerequisites:                                                  ║
║    Set DEEPSEEK_API_KEY in .env                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import ResearchOrchestrator
from core.problem_classifier import classify_problem


# ─── Problem catalogue ──────────────────────────────────────────

PROBLEMS = {
    "cmp": {
        "name": "1D Tight-Binding DOS Derivation",
        "hamiltonian": (
            "H = -t * Sum(c_dagger_i * c_j, (i, j)) (Nearest-Neighbor)"
        ),
        "integrand": (
            "1 / (2*pi) * Integral(SpectralFunction(k, omega), (k, -pi, pi))"
        ),
        "bounds": "[-pi, pi]",
        "parameters": ["t=1.0", "eta=0.01"],
        "target": (
            "Find the general analytic expression for the Density of States "
            "D(omega)."
        ),
        "hint": (
            "1. Fourier transform sites {i, j} to k-space. "
            "2. eps(k) = -2t cos(ka). "
            "3. G = 1/(omega - eps(k) + I*eta). "
            "4. D(omega) = -1/pi * Im[Integral G dk]."
        ),
    },
    "integral": {
        "name": "Parametric Sinusoidal Decay Integral",
        "integrand": "sin(a*x) / (x * (x**2 + 1))",
        "bounds": "[0, oo]",
        "parameters": ["a=1"],
        "target": "Evaluate the integral analytically.",
    },
    "bcs": {
        "name": "BCS Gap Equation Derivation",
        "hamiltonian": (
            "H = Sum(epsilon_k * c^dag_k_sigma * c_k_sigma, k, sigma) "
            "- V * Sum(c^dag_k_up * c^dag_{-k}_down * c_{-k'}_down * c_{k'}_up, k, k')"
        ),
        "integrand": (
            "Integral(Delta / (2*E_k) * tanh(beta*E_k/2), (k, -pi, pi))"
        ),
        "bounds": "[-pi, pi]",
        "parameters": ["t=1.0", "V=0.5", "beta=10.0"],
        "target": (
            "Derive the finite-temperature self-consistent BCS gap equation: "
            "Delta = V * Sum_k Delta / (2*E_k) * tanh(beta*E_k/2)"
        ),
        "hint": (
            "1. Write anomalous Green's function F(k,iw_n). "
            "2. Self-energy from Feynman diagram. "
            "3. Matsubara sum over iw_n. "
            "4. Obtain self-consistent gap equation."
        ),
    },
    "weyl": {
        "name": "Anomalous Hall Conductivity of 2D Massive Dirac Fermion",
        "hamiltonian": (
            "H = v * kx * sigma_x + v * ky * sigma_y + m * sigma_z"
        ),
        "target": (
            "Derive the zero-temperature anomalous Hall conductivity sigma_xy. "
            "You MUST use the TopologyEngine to compute the Berry curvature Omega_z "
            "for the lowest energy band (n=0), then integrate it over the 2D plane from -oo to oo."
        ),
        "hint": (
            "1. Activate 'topology_engine' and 'transport_engine'. "
            "2. Compute Omega_z(kx, ky) for the lowest energy band. "
            "3. Integrate Omega_z over dkx dky from -oo to oo (or use polar coordinates k, theta). "
            "4. Prove that sigma_xy evaluates to a topological invariant proportional to sgn(m)."
        ),
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="NeuroSymbolic Solver — LLM-powered end-to-end demo"
    )
    parser.add_argument(
        "--problem",
        choices=list(PROBLEMS.keys()),
        default="cmp",
        help="Which problem to solve (default: cmp)",
    )
    parser.add_argument(
        "--lang", default="Chinese",
        help="Report language (default: Chinese)",
    )
    parser.add_argument(
        "--max-iter", type=int, default=15,
        help="Max search iterations (default: 15)",
    )
    args = parser.parse_args()

    # ── Pre-flight check ─────────────────────────────────────────
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("="*60)
        print("  ERROR: DEEPSEEK_API_KEY not set!")
        print("  This demo requires a DeepSeek API key.")
        print("  Set it in .env: DEEPSEEK_API_KEY=sk-...")
        print("="*60)
        sys.exit(1)

    problem = PROBLEMS[args.problem]

    # ── Show what the classifier detects ─────────────────────────
    print("╔" + "═"*58 + "╗")
    print("║  NeuroSymbolic Physics Solver — LLM Pipeline             ║")
    print("╚" + "═"*58 + "╝")
    print()

    profile = classify_problem(problem)
    print(f"  Problem   : {problem['name']}")
    print(f"  Domains   : {profile.domains}")
    print(f"  Engines   : {profile.engines or '(none — pure math mode)'}")
    print(f"  Verify    : {profile.verify_strategy}")
    print(f"  CMP mode  : {profile.cmp_mode}")
    print()
    print("  The following LLM agents will participate:")
    print("    🧠 Theorist  (DeepSeek-R1)  — symbolic reasoning")
    print("    💻 Coder     (DeepSeek-V3)  — Python implementation")
    print("    🔍 Verifier  (DeepSeek-V3)  — execution & critique")
    print("    📝 Reporter  (DeepSeek-V3)  — scientific report writing")
    print()
    print("─"*60)
    # input("  Press Enter to start the LLM-powered solver...\n")

    # ── Launch ───────────────────────────────────────────────────
    orch = ResearchOrchestrator(problem, report_language=args.lang)
    orch.max_iterations = args.max_iter
    orch.run()


if __name__ == "__main__":
    main()
