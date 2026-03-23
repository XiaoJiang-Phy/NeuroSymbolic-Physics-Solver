"""
ResearchOrchestrator v2 – Unified, self‑routing solver.

On receiving a problem dict the orchestrator:
  1. Calls the ProblemClassifier to determine domains, engines, and
     verification strategy.
  2. Dynamically activates only the engines and audits required.
  3. Runs the Best‑First Search loop, automatically choosing between
     Numerical Oracle, Physics Audit, or Hybrid verification per step.
"""

import os
import sys
import json
import re
import heapq
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is on sys.path regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.theorist_agent import TheoristAgent
from agents.coder_agent import CoderAgent
from agents.verifier_agent import VerifierAgent
from agents.reporter_agent import ReporterAgent
from utils.numerical_oracle import get_oracle
from utils.physics_auditor import get_physics_auditor

from core.problem_classifier import (
    classify_problem,
    ProblemProfile,
    Domain,
    VerifyStrategy,
    Engine,
)


class ResearchOrchestrator:
    """
    Unified solver that auto‑detects problem type and activates engines.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def __init__(self, problem_definition: dict, report_language: str = "English"):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

        self.problem = problem_definition
        self.report_language = report_language

        # ── Auto‑classify ──
        self.profile: ProblemProfile = classify_problem(problem_definition)
        print(f"\n{'='*60}")
        print(f" [Classifier] {self.profile.summary}")
        print(f"{'='*60}\n")

        # ── Core agents (always present) ──
        self.theorist = TheoristAgent()
        self.coder    = CoderAgent()
        self.verifier = VerifierAgent()
        self.reporter = ReporterAgent()
        self.oracle   = get_oracle()
        self.auditor  = get_physics_auditor()

        # ── Dynamically‑loaded engines ──
        self.engines: dict = {}
        self._load_engines()

        # ── Search state ──
        self.state            = "INIT"
        self.max_iterations   = 15
        self.log_path         = "tree_log.json"
        self.tree_log         = self._load_tree_log()
        self.history          = []
        self.banned_strategies = set()
        self.failed_verdicts  = []

    # ------------------------------------------------------------------
    # Dynamic engine loading
    # ------------------------------------------------------------------
    def _load_engines(self):
        """Instantiate only the engines required by the classifier."""
        if Engine.MATSUBARA in self.profile.engines:
            from utils.matsubara_engine import get_matsubara_engine
            self.engines[Engine.MATSUBARA] = get_matsubara_engine()
            print(f"  [Engine] Matsubara Frequency Engine  ✓")

        if Engine.FEYNMAN in self.profile.engines:
            from utils.feynman_translator import get_feynman_translator
            self.engines[Engine.FEYNMAN] = get_feynman_translator()
            print(f"  [Engine] Feynman Diagram Translator  ✓")

        if Engine.RG in self.profile.engines:
            from utils.rg_operator import get_rg_operator
            self.engines[Engine.RG] = get_rg_operator()
            print(f"  [Engine] RG Operator                 ✓")

        if not self.engines:
            print(f"  [Engine] No specialised engines needed (pure math mode).")

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_tree_log(self) -> dict:
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding='utf-8') as f:
                    print(f"[Orchestrator] Resuming from {self.log_path}")
                    return json.load(f)
            except Exception as e:
                print(f"[Orchestrator] Error loading tree log: {e}")
        return {}

    def _save_tree_log(self):
        try:
            with open(self.log_path, "w", encoding='utf-8') as f:
                json.dump(self.tree_log, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Orchestrator] Error saving tree log: {e}")

    # ------------------------------------------------------------------
    # Expression cleaning
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_math_expr(expr_str: str) -> str:
        if not expr_str:
            return ""
        s = str(expr_str).strip()
        for label in ("f(x, a) =", "I(a) =", "New Integrand:"):
            if s.startswith(label):
                s = s[len(label):].strip()
        if s.startswith("```"):
            s = s.strip("`").replace("python", "").replace("sympy", "").strip()
        s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)
        return s

    # ------------------------------------------------------------------
    # Context distillation
    # ------------------------------------------------------------------
    def _distill_context(self, current_node: dict) -> dict:
        return {
            "successful_path": [
                {
                    "action": step.get("action_type"),
                    "expr": step.get("sympy_code"),
                    "logic": (step.get("logic") or "")[:200] + "...",
                }
                for step in current_node["path"]
            ],
            "failed_attempts_verdicts": self.failed_verdicts[-10:],
            "banned_strategies": list(self.banned_strategies),
            # Expose activated engines so the Theorist knows what tools it has
            "active_engines": list(self.engines.keys()),
            "problem_profile": {
                "primary_domain": self.profile.primary_domain,
                "verify_strategy": self.profile.verify_strategy,
            },
        }

    # ------------------------------------------------------------------
    # Step verification dispatcher
    # ------------------------------------------------------------------
    def _verify_step(self, parent_expr: str, child_expr: str,
                     action: str, prob: float) -> bool:
        """
        Returns True if the step should be ACCEPTED, False otherwise.
        Dispatches to the correct strategy based on ProblemProfile.
        """
        strategy = self.profile.verify_strategy

        if strategy == VerifyStrategy.NUMERICAL_ORACLE:
            return self._verify_numerical(parent_expr, child_expr, action, prob)

        elif strategy == VerifyStrategy.PHYSICS_AUDIT:
            return self._verify_physics(parent_expr, child_expr, action, prob)

        elif strategy == VerifyStrategy.HYBRID:
            # Try numerical first; fall back to physics audit if oracle cannot evaluate CMP expressions
            numerical_ok = self._verify_numerical(parent_expr, child_expr, action, prob)
            if numerical_ok is None:
                # Oracle returned None → CMP expression; switch to physics audit
                return self._verify_physics(parent_expr, child_expr, action, prob)
            return numerical_ok

        # Fallback: accept if probability is high enough
        return prob >= 0.7

    def _verify_numerical(self, parent_expr, child_expr, action, prob):
        """Standard Oracle‑based numerical verification. Returns True/False/None."""
        try:
            matches = []

            p_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
            c_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
            if p_val is not None and c_val is not None:
                matches.append(abs(p_val - c_val))

            if "integration" in action.lower() or "integrating" in action.lower():
                c_deriv = self.oracle.evaluate_derivative(self.problem, child_expr, wrt='a')
                if p_val is not None and c_deriv is not None:
                    matches.append(abs(p_val - c_deriv))

            if "differentiation" in action.lower() or "differentiating" in action.lower():
                p_deriv = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
                if p_deriv is not None and c_val is not None:
                    matches.append(abs(p_deriv - c_val))

            if not matches:
                if prob < 0.7:
                    print(f"    [Warning] Oracle evaluation failed & low p={prob}.")
                    return False
                return None  # Signal caller to fall back

            best_diff = min(matches)
            if best_diff > 1e-3:
                print(f"    [Invalid] Numerical mismatch ({best_diff:.2e})")
                return False
            return True

        except Exception as e:
            print(f"    [Error] Oracle exception: {e}")
            return None

    def _verify_physics(self, parent_expr, child_expr, action, prob):
        """CMP / physics‑audit verification."""
        # ── Causality check (Green's function context) ──
        if "causality" in self.profile.physics_audits:
            if any(kw in child_expr for kw in ['1 /', 'G =', 'Green']) and 'eta' in parent_expr:
                ok, msg = self.auditor.audit_causality(child_expr)
                if not ok:
                    print(f"    [Physics Audit FAIL] {msg}")
                    self.auditor.log_decision(
                        context=f"Action: {action}, Expr: {child_expr[:40]}…",
                        hypothesis=f"Applying {action}.",
                        failure_mode=msg,
                        causality="Missing i*eta convention.",
                        pivot="Discarding branch.",
                    )
                    return False

        # ── Probability gate ──
        if prob < 0.7:
            print(f"    [CMP] Low probability ({prob}), skipping.")
            return False

        print(f"    [CMP] Accepted (Physics Audit passed, p={prob}).")
        return True

    # ------------------------------------------------------------------
    # Main search loop
    # ------------------------------------------------------------------
    def run(self):
        log_mode = "w" if not self.tree_log else "a"
        with open("thinking_process.txt", log_mode, encoding='utf-8') as f:
            f.write(f"\n\n{'='*20} Search Start: {self.problem['name']} {'='*20}\n")

        print(f"--- Launching Solver for: {self.problem['name']} ---")
        print(f"    Strategy: {self.profile.verify_strategy}")
        print(f"    CMP mode: {self.profile.cmp_mode}\n")

        self.queue = []
        initial_expr = self.problem.get('integrand', '')
        if initial_expr and "Integral" not in initial_expr:
            bounds = self.problem.get('bounds', '[0, oo]').strip('[]').split(',')
            initial_expr = f"Integral({initial_expr}, (x, {bounds[0].strip()}, {bounds[1].strip()}))"

        start_node = {
            "expression": initial_expr or self.problem.get('hamiltonian', ''),
            "latex": initial_expr,
            "depth": 0,
            "path": [],
        }

        if self.tree_log:
            last_key = list(self.tree_log.keys())[-1]
            last = self.tree_log[last_key]
            start_node = {
                "expression": last['to'],
                "latex": last.get('latex', last['to']),
                "depth": int(last_key.split("_")[-1]),
                "path": list(self.tree_log.values()),
            }

        self.counter = 0
        heapq.heappush(self.queue, (-1.0, start_node['depth'], self.counter, start_node))
        self.counter += 1

        visited = set()
        iteration = 0

        while self.queue and iteration < self.max_iterations:
            neg_pri, depth, _, current = heapq.heappop(self.queue)
            iteration += 1

            expr_str = self._clean_math_expr(current['expression'])
            if expr_str in visited:
                continue
            visited.add(expr_str)

            print(f"\n[Step {iteration}] depth={depth}  priority={-neg_pri:.2f}")
            print(f"  Expr: {expr_str[:120]}{'…' if len(expr_str) > 120 else ''}")

            ctx = self._distill_context(current)
            ctx["search_depth"] = depth

            proposals = self.theorist.solve(self.problem, context=ctx)
            if not isinstance(proposals, list):
                continue

            for step in proposals:
                action = step.get('action_type', 'Transform')
                if action in self.banned_strategies:
                    print(f"  > Skipping banned: {action}")
                    continue

                child_expr = self._clean_math_expr(step.get('sympy_code', ''))
                prob       = step.get('success_probability', 0.5)
                simplicity = step.get('simplicity_score', 5)

                print(f"  > Considering: {action}  (p={prob}, s={simplicity})")

                accepted = self._verify_step(
                    current['expression'], child_expr, action, prob
                )
                if not accepted:
                    continue

                new_node = {
                    "expression": child_expr,
                    "latex": step.get('intermediate_expression'),
                    "depth": depth + 1,
                    "path": current['path'] + [step],
                }

                if step.get('is_terminal'):
                    print(f"    [Terminal] Verifying final result…")
                    oracle_val   = self.oracle.evaluate_ground_truth(self.problem)
                    oracle_limit = self.oracle.evaluate_asymptotic_limit(self.problem, child_expr)

                    impl = self.coder.generate_implementation(self.problem, step)

                    script = f"eval_terminal_{iteration}.py"
                    with open(script, "w", encoding='utf-8') as f:
                        f.write(impl.get("python_script", ""))

                    vr = self.verifier.verify(script, oracle_val, oracle_limit=oracle_limit)
                    if vr.get("status") == "SUCCESS":
                        print(f"    [SUCCESS] Solution verified!")
                        self._finalize(step, new_node['path'])
                        return
                    else:
                        verdict = vr.get("verdict") or "Unknown"
                        res = vr.get("residual", "N/A")
                        print(f"    [Pruned] Residual={res}  Verdict={verdict}")

                        self.failed_verdicts.append(
                            f"[Verdict: {action} failed@d{depth}. Res={res}. {str(verdict)[:100]}]"
                        )
                        if "Type B" in str(verdict):
                            self.banned_strategies.add(action)

                        self.auditor.log_decision(
                            context=f"Terminal: {child_expr[:50]}…",
                            hypothesis="Candidate = final solution.",
                            failure_mode=f"Residual={res}",
                            causality="Math/Sum‑Rule violation.",
                            pivot="Prune & ban if Type B.",
                        )
                else:
                    priority = (prob * 0.7 + (simplicity / 10.0) * 0.3) * (0.85 ** depth)
                    heapq.heappush(self.queue, (-priority, depth + 1, self.counter, new_node))
                    self.counter += 1

                    sid = len(self.tree_log) + 1
                    self.tree_log[f"Checkpoint_{sid}"] = {
                        "from": current['expression'],
                        "to": child_expr,
                        "action": action,
                        "logic": step.get('logic'),
                        "latex": step.get('intermediate_expression'),
                        "prob": prob,
                        "simplicity": simplicity,
                    }
                    self._save_tree_log()

        print("\n[Halt] Search exhausted.")
        self.reporter.generate_report(
            self.problem, self.tree_log, "thinking_process.txt",
            language=self.report_language,
        )

    # ------------------------------------------------------------------
    # Finalisation
    # ------------------------------------------------------------------
    def _finalize(self, result, full_path):
        print("\n--- Compiling Scientific Report ---")
        self.reporter.generate_report(
            self.problem, self.tree_log, "thinking_process.txt",
            final_solution=result, language=self.report_language,
        )


# ======================================================================
# CLI entry‑point
# ======================================================================
if __name__ == "__main__":
    # ── Example 1: CMP – will auto‑classify as greens_function + many_body ──
    cmp_problem = {
        "name": "1D Tight-Binding DOS Derivation",
        "hamiltonian": "H = -t * Sum(c_dagger_i * c_j, (i, j)) (Nearest-Neighbor)",
        "integrand": "1 / (2*pi) * Integral(SpectralFunction(k, omega), (k, -pi, pi))",
        "bounds": "[-pi, pi]",
        "parameters": ["t=1.0", "eta=0.01"],
        "target": "Find the general analytic expression for the Density of States D(omega).",
        "hint": "1. Fourier transform sites {i,j} to k-space. "
                "2. eps(k)=-2t cos(ka). "
                "3. G=1/(omega-eps(k)+I*eta). "
                "4. D(omega)=-1/pi * Im[Integral G dk].",
    }

    # ── Example 2: Pure integral ──
    integral_problem = {
        "name": "Parametric Sinusoidal Decay Integral",
        "integrand": "sin(a*x) / (x * (x**2 + 1))",
        "bounds": "[0, oo]",
        "parameters": ["a=1"],
        "target": "Evaluate the integral analytically.",
    }

    # ── Pick a problem ──
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", choices=["cmp", "integral"], default="cmp")
    parser.add_argument("--lang", default="Chinese")
    args = parser.parse_args()

    prob = cmp_problem if args.problem == "cmp" else integral_problem
    orchestrator = ResearchOrchestrator(prob, report_language=args.lang)
    orchestrator.run()
