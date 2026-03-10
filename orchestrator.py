import os
import json
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

from agents.theorist_agent import TheoristAgent
from agents.coder_agent import CoderAgent
from agents.verifier_agent import VerifierAgent
from agents.reporter_agent import ReporterAgent
from utils.numerical_oracle import get_oracle

class ResearchOrchestrator:
    def __init__(self, problem_definition, report_language="English"):
        self.problem = problem_definition
        self.theorist = TheoristAgent()
        self.coder = CoderAgent()
        self.verifier = VerifierAgent()
        self.reporter = ReporterAgent()
        self.oracle = get_oracle()
        self.state = "INIT"
        self.max_iterations = 10
        self.log_path = "tree_log.json"
        self.tree_log = self._load_tree_log()
        self.report_language = report_language
        self.history = []

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
        s = expr_str.strip()
        # Remove common labels but KEEP the equation if it is meaningful
        labels = ["f(x, a) =", "I(a) =", "New Integrand:"]
        for label in labels:
            if s.startswith(label):
                s = s[len(label):].strip()
        
        # Don't strip Eq() anymore! We WANT Eq(lhs, rhs) for transformations.
        # But if it starts with '```python' or something, clean that.
        if s.startswith("```"):
            s = s.strip("`").replace("python", "").replace("sympy", "").strip()
            
        return s

    def run(self):
        import heapq
        
        # Initialize/Clear thinking process log
        log_mode = "w" if not self.tree_log else "a"
        with open("thinking_process.txt", log_mode, encoding='utf-8') as f:
            f.write(f"\n\n{'='*20} Search Resume/Start: {self.problem['name']} {'='*20}\n")
        
        print(f"--- Launching Physics-Aware Solver for: {self.problem['name']} ---")
        
        # Open set for Best-First Search: (neg_priority, depth, state_dict)
        # We use negative priority for max-heap behavior
        self.queue = []
        
        initial_expr = self.problem['integrand']
        # Initial wrap for integration
        if "Integral" not in initial_expr:
            bounds = self.problem.get('bounds', '[0, oo]').strip('[]').split(',')
            initial_expr = f"Integral({initial_expr}, (x, {bounds[0].strip()}, {bounds[1].strip()}))"
            
        start_node = {
            "expression": initial_expr,
            "latex": initial_expr,
            "depth": 0,
            "path": []
        }
        
        # If resuming, load the last successful state as the root of a new search or reconstruct queue
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

        # Tie-breaker counter for heapq
        self.counter = 0
        heapq.heappush(self.queue, (-1.0, start_node['depth'], self.counter, start_node))
        self.counter += 1
        
        visited_expressions = set()
        iteration_count = 0
        
        while self.queue and iteration_count < self.max_iterations:
            neg_prob, depth, cnt, current = heapq.heappop(self.queue)
            iteration_count += 1
            
            expr_str = self._clean_math_expr(current['expression'])
            if expr_str in visited_expressions:
                continue
            visited_expressions.add(expr_str)
            
            print(f"\n[Search Step {iteration_count}] Depth: {depth}, Prob: {-neg_prob:.2f}")
            print(f"Current Expression: {expr_str}")
            
            # Prepare context for Theorist
            context_to_pass = {
                "current_state": current,
                "derivation_path": current['path'],
                "search_depth": depth,
                "physics_audit_required": True
            }
            
            proposals = self.theorist.solve(self.problem, context=context_to_pass)
            if not isinstance(proposals, list):
                continue

            for step in proposals:
                action = step.get('action_type', 'Transform')
                child_expr = self._clean_math_expr(step.get('sympy_code', ''))
                prob = step.get('success_probability', 0.5)
                
                print(f"  > Considering: {action} (p={prob})")
                
                # Numerical Equivalence Check
                try:
                    # Verification Match Check
                    parent_expr = current['expression']
                    
                    # Determine possible matches
                    matches = []
                    
                    # Choice 1: Direct Equivalence
                    p_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
                    c_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
                    if p_val is not None and c_val is not None:
                        matches.append(abs(p_val - c_val))
                    
                    # Choice 2: Parent is Derivative of Child (Integration step)
                    if "integration" in action.lower() or "integrating" in action.lower():
                        c_deriv_val = self.oracle.evaluate_derivative(self.problem, child_expr, wrt='a')
                        if p_val is not None and c_deriv_val is not None:
                            matches.append(abs(p_val - c_deriv_val))
                            
                    # Choice 3: Child is Derivative of Parent (Differentiation step)
                    if "differentiation" in action.lower() or "differentiating" in action.lower():
                        p_deriv_val = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
                        if p_deriv_val is not None and c_val is not None:
                            matches.append(abs(p_deriv_val - c_val))

                    # Success if ANY match works
                    if not matches:
                        print(f"    [Warning] Oracle evaluation failed for this branch.")
                        if prob < 0.7: continue
                    else:
                        best_diff = min(matches)
                        # Relaxed check for complex derivations
                        if best_diff > 1e-3:
                            print(f"    [Invalid] Numerical mismatch (Best Diff: {best_diff})")
                            continue
 
                except Exception as e:
                    print(f"    [Error] Exception during validation: {e}")
                    continue

                new_node = {
                    "expression": child_expr,
                    "latex": step.get('intermediate_expression'),
                    "depth": depth + 1,
                    "path": current['path'] + [step]
                }
                
                # Terminal Check
                if step.get('is_terminal'):
                    print(f"    [Terminal] Target reached. Verifying final result...")
                    oracle_val = self.oracle.evaluate_ground_truth(self.problem)
                    # We don't pass oracle_val as a point sampler for the FINAL result comparison
                    implementation = self.coder.generate_implementation(self.problem, step)
                    
                    script_path = f"eval_terminal_{iteration_count}.py"
                    with open(script_path, "w", encoding='utf-8') as f:
                        f.write(implementation.get("python_script", ""))
                    
                    verification_result = self.verifier.verify(script_path, oracle_val)
                    if verification_result.get("status") == "SUCCESS":
                        print(f"    [SUCCESS] Solution Verified!")
                        self.finalize(step, new_node['path'])
                        return
                    else:
                        critique = verification_result.get("verdict") or verification_result.get("critique") or "Unknown error"
                        res = verification_result.get("residual", "N/A")
                        print(f"    [Pruned] Terminal verification failed. Residual: {res}. Critique: {critique}")
                else:
                    # Generic Node: Push to Queue
                    # Priority is boosted by success_probability and penalized by depth
                    priority = prob * (0.9 ** depth)
                    heapq.heappush(self.queue, (-priority, depth + 1, self.counter, new_node))
                    self.counter += 1
                    
                    # Log successful steps to tree_log for global visibility
                    step_id = len(self.tree_log) + 1
                    self.tree_log[f"Checkpoint_{step_id}"] = {
                        "from": current['expression'],
                        "to": child_expr,
                        "action": action,
                        "logic": step.get('logic'),
                        "latex": step.get('intermediate_expression'),
                        "prob": prob
                    }
                    self._save_tree_log()

        print("\n[Halt] Search space exhausted or max iterations reached.")
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", language=self.report_language)

    def finalize(self, result, full_path):
        print("\n--- Compiling Final Scientific Report ---")
        # Synthesize the full path for the reporter
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", final_solution=result, language=self.report_language)

if __name__ == "__main__":
    problem = {
            "name": "Parametric Sinusoidal Decay Integral",
            "integrand": "sin(a*x) / (x * (x**2 + 1))",
            "bounds": "[0, oo]",
            "parameters": ["a=1", "a=2", "a=5"],
            "target": "Find the general closed-form solution as a function of parameter 'a' (a > 0).",
            "hint": "Consider partial fraction decomposition: 1/(x(x^2+1)) = 1/x - x/(x^2+1), or differentiation under the integral sign with respect to 'a'."
    }
    orchestrator = ResearchOrchestrator(problem, report_language="Chinese")
    orchestrator.run()
