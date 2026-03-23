import os
import json
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.theorist_agent import TheoristAgent
from agents.coder_agent import CoderAgent
from agents.verifier_agent import VerifierAgent
from agents.reporter_agent import ReporterAgent
from utils.numerical_oracle import get_oracle
from utils.physics_auditor import get_physics_auditor

class ResearchOrchestrator:
    def __init__(self, problem_definition, report_language="English"):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        self.problem = problem_definition
        self.theorist = TheoristAgent()
        self.coder = CoderAgent()
        self.verifier = VerifierAgent()
        self.reporter = ReporterAgent()
        self.oracle = get_oracle()
        self.auditor = get_physics_auditor()
        self.state = "INIT"
        self.max_iterations = 15
        self.log_path = "tree_log.json"
        self.tree_log = self._load_tree_log()
        self.report_language = report_language
        self.history = []
        self.banned_strategies = set()
        self.failed_verdicts = [] # For context distillation

    def _load_tree_log(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding='utf-8') as f:
                    print(f"[Orchestrator] Loading existing tree log from {self.log_path}")
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

    def _clean_math_expr(self, expr_str):
        if not expr_str: return ""
        s = str(expr_str).strip()
        # Remove common labels but KEEP the equation if it is meaningful
        labels = ["f(x, a) =", "I(a) =", "New Integrand:"]
        for label in labels:
            if s.startswith(label):
                s = s[len(label):].strip()
        
        # Don't strip Eq() anymore! We WANT Eq(lhs, rhs) for transformations.
        if s.startswith("```"):
            s = s.strip("`").replace("python", "").replace("sympy", "").strip()
            
        import re
        s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)
        return s

    def _distill_context(self, current_node):
        """
        Principle 4: 精简上下文 (Context Distillation)
        Removes redundant code from failed paths, keeping only brief mathematical verdicts.
        """
        distilled = {
            "successful_path": [
                {
                    "action": step.get("action_type"),
                    "expr": step.get("sympy_code"),
                    "logic": step.get("logic")[:200] + "..." # Truncate long logic
                } for step in current_node['path']
            ],
            "failed_attempts_verdicts": self.failed_verdicts[-10:], # Keep last 10 failed verdicts
            "banned_strategies": list(self.banned_strategies)
        }
        return distilled

    def run(self):
        import heapq
        
        log_mode = "w" if not self.tree_log else "a"
        with open("thinking_process.txt", log_mode, encoding='utf-8') as f:
            f.write(f"\n\n{'='*20} Search Resume/Start: {self.problem['name']} {'='*20}\n")
        
        print(f"--- Launching Physics-Aware Solver for: {self.problem['name']} ---")
        
        self.queue = []
        initial_expr = self.problem['integrand']
        if "Integral" not in initial_expr:
            bounds = self.problem.get('bounds', '[0, oo]').strip('[]').split(',')
            initial_expr = f"Integral({initial_expr}, (x, {bounds[0].strip()}, {bounds[1].strip()}))"
            
        start_node = {
            "expression": initial_expr,
            "latex": initial_expr,
            "depth": 0,
            "path": []
        }
        
        if self.tree_log:
            last_step_key = list(self.tree_log.keys())[-1]
            last_step = self.tree_log[last_step_key]
            print(f"[Orchestrator] Resuming search from checkpoint: {last_step_key}")
            start_node = {
                "expression": last_step['to'],
                "latex": last_step.get('latex', last_step['to']),
                "depth": int(last_step_key.split("_")[-1]),
                "path": list(self.tree_log.values())
            }

        self.counter = 0
        heapq.heappush(self.queue, (-1.0, start_node['depth'], self.counter, start_node))
        self.counter += 1
        
        visited_expressions = set()
        iteration_count = 0
        
        while self.queue and iteration_count < self.max_iterations:
            neg_priority, depth, cnt, current = heapq.heappop(self.queue)
            iteration_count += 1
            
            expr_str = self._clean_math_expr(current['expression'])
            if expr_str in visited_expressions:
                continue
            visited_expressions.add(expr_str)
            
            print(f"\n[Search Step {iteration_count}] Depth: {depth}, Priority: {-neg_priority:.2f}")
            print(f"Current Expression: {expr_str}")
            
            context_to_pass = self._distill_context(current)
            context_to_pass["search_depth"] = depth
            
            proposals = self.theorist.solve(self.problem, context=context_to_pass)
            if not isinstance(proposals, list):
                continue

            for step in proposals:
                action = step.get('action_type', 'Transform')
                if action in self.banned_strategies:
                    print(f"  > Skipping banned strategy: {action}")
                    continue
                    
                child_expr = self._clean_math_expr(step.get('sympy_code', ''))
                prob = step.get('success_probability', 0.5)
                simplicity = step.get('simplicity_score', 5)
                
                print(f"  > Considering: {action} (p={prob}, s={simplicity})")
                
                try:
                    parent_expr = current['expression']
                    
                    # CMP Mode: Skip Oracle intermediate checks for CMP problems
                    # CMP expressions (DiracDelta, Heaviside, operator algebra, etc.)
                    # cannot be numerically evaluated by the Oracle.
                    is_cmp = 'Tight-Binding' in self.problem.get('name', '') or 'DOS' in self.problem.get('name', '')
                    
                    if is_cmp:
                        # Phase 2: Physics Audit - Causality Check (2.2)
                        # Green's Functions and spectral representations must preserve causality (i*eta)
                        if any(kw in child_expr for kw in ['1 /', 'G =', 'Green']) and 'eta' in parent_expr:
                            causal_ok, causal_msg = self.auditor.audit_causality(child_expr)
                            if not causal_ok:
                                print(f"    [Physics Audit FAIL] {causal_msg}")
                                self.auditor.log_decision(
                                    context=f"Action: {action}, Expression: {child_expr[:40]}...",
                                    hypothesis=f"Applying {action} to advance derivation.",
                                    failure_mode=causal_msg,
                                    causality="Transformation erroneously discarded the infinitesimal imaginary part required for analytic properties.",
                                    pivot="Discarding branch to preserve physical spectrum causality."
                                )
                                continue

                        # Trust the Theorist's probability score for CMP problems
                        if prob < 0.7:
                            print(f"    [CMP] Low probability ({prob}), skipping.")
                            continue
                        print(f"    [CMP] Accepted (Oracle bypass, trusting p={prob}, Physics Audit Passed).")
                    else:
                        # Standard mode: numerical Oracle verification
                        matches = []
                        
                        p_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
                        c_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
                        if p_val is not None and c_val is not None:
                            matches.append(abs(p_val - c_val))
                        
                        if "integration" in action.lower() or "integrating" in action.lower():
                            c_deriv_val = self.oracle.evaluate_derivative(self.problem, child_expr, wrt='a')
                            if p_val is not None and c_deriv_val is not None:
                                matches.append(abs(p_val - c_deriv_val))
                                
                        if "differentiation" in action.lower() or "differentiating" in action.lower():
                            p_deriv_val = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
                            if p_deriv_val is not None and c_val is not None:
                                matches.append(abs(p_deriv_val - c_val))

                        if not matches:
                            print(f"    [Warning] Oracle evaluation failed.")
                            if prob < 0.7: continue
                        else:
                            best_diff = min(matches)
                            if best_diff > 1e-3:
                                print(f"    [Invalid] Numerical mismatch ({best_diff})")
                                continue
  
                except Exception as e:
                    print(f"    [Error] Validation exception: {e}")
                    continue


                new_node = {
                    "expression": child_expr,
                    "latex": step.get('intermediate_expression'),
                    "depth": depth + 1,
                    "path": current['path'] + [step]
                }
                
                if step.get('is_terminal'):
                    print(f"    [Terminal] Target reached. Verifying final result...")
                    oracle_val = self.oracle.evaluate_ground_truth(self.problem)
                    oracle_limit = self.oracle.evaluate_asymptotic_limit(self.problem, child_expr)
                    
                    implementation = self.coder.generate_implementation(self.problem, step)
                    
                    script_path = f"eval_terminal_{iteration_count}.py"
                    with open(script_path, "w", encoding='utf-8') as f:
                        f.write(implementation.get("python_script", ""))
                    
                    verification_result = self.verifier.verify(script_path, oracle_val, oracle_limit=oracle_limit)
                    if verification_result.get("status") == "SUCCESS":
                        print(f"    [SUCCESS] Solution Verified!")
                        self.finalize(step, new_node['path'])
                        return
                    else:
                        verdict = verification_result.get("verdict") or "Unknown error"
                        res = verification_result.get("residual", "N/A")
                        print(f"    [Pruned] Failed. Residual: {res}. Verdict: {verdict}")
                        
                        # Principle 4: Store Distilled Verdict
                        self.failed_verdicts.append(f"[Mathematica Verdict: {action} failed at depth {depth}. Residual: {res}. {verdict[:100]}]")
                        
                        # Principle 3: Permanent Banning of Type B strategies
                        if "Type B" in verdict:
                            print(f"    [Banned] Strategy '{action}' added to banned list due to Type B error.")
                            self.banned_strategies.add(action)
                            
                        # If a terminal test failed via the verification stage (e.g. Sum Rule 2.3), log it in the physics audit:
                        self.auditor.log_decision(
                            context=f"Terminal Output Verification: {child_expr[:50]}...",
                            hypothesis="Candidate represented final analytical solution.",
                            failure_mode=f"Verification failure (Residual: {res}).",
                            causality=f"Mathematical bounds or Sum Rule violation resulting in Type {'B' if 'Type B' in verdict else 'A'} deviation.",
                            pivot="Pruning branch and blacklisting if Type B."
                        )
                else:
                    # Generic Node: Push to Queue
                    # Principle A: Priority uses (prob * 0.7 + (simplicity/10) * 0.3) and depth penalty
                    priority = (prob * 0.7 + (simplicity / 10.0) * 0.3) * (0.85 ** depth)
                    heapq.heappush(self.queue, (-priority, depth + 1, self.counter, new_node))
                    self.counter += 1
                    
                    step_id = len(self.tree_log) + 1
                    self.tree_log[f"Checkpoint_{step_id}"] = {
                        "from": current['expression'],
                        "to": child_expr,
                        "action": action,
                        "logic": step.get('logic'),
                        "latex": step.get('intermediate_expression'),
                        "prob": prob,
                        "simplicity": simplicity
                    }
                    self._save_tree_log()

        print("\n[Halt] Search exhaustion.")
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", language=self.report_language)

    def finalize(self, result, full_path):
        print("\n--- Compiling Final Scientific Report ---")
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", final_solution=result, language=self.report_language)

if __name__ == "__main__":
    problem = {
            "name": "1D Tight-Binding DOS Derivation",
            "hamiltonian": "H = -t * Sum(c_dagger_i * c_j, (i, j)) (Nearest-Neighbor)",
            "integrand": "1 / (2*pi) * Integral(SpectralFunction(k, omega), (k, -pi, pi))",
            "bounds": "[-pi, pi]",
            "parameters": ["t=1.0", "eta=0.01"],
            "target": "Find the general analytic expression for the Density of States D(omega).",
            "hint": "1. Fourier transform sites {i, j} to k-space. 2. eps(k) = -2t cos(ka). 3. G = 1/(omega - eps(k) + I*eta). 4. D(omega) = -1/pi * Im[Integral G dk]."
    }
    orchestrator = ResearchOrchestrator(problem, report_language="Chinese")
    orchestrator.run()
