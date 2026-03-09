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
        # Strip "f(x, a) = " or "I(a) = "
        if "=" in s:
            s = s.split("=")[-1].strip()
        # Strip "Eq(" wrapper if Theorist agent added one
        if s.startswith("Eq(") and s.endswith(")"):
            # Simple but cautious extraction of RHS (second argument)
            # This is a bit risky for complex Eq(LHS, RHS) but good as a first pass
            parts = s[3:-1].split(",", 1)
            if len(parts) == 2:
                s = parts[1].strip()
        return s

    def run(self):
        # Initialize/Clear thinking process log
        with open("thinking_process.txt", "w", encoding='utf-8') as f:
            f.write(f"Step-wise Research Log for: {self.problem['name']}\n")
            f.write("="*50 + "\n")

        print(f"--- Initializing Reasoning Tree for: {self.problem['name']} ---")
        
        # Current state of the derivation
        self.current_state = {
            "expression": self.problem['integrand'],
            "latex": self.problem['integrand'],
            "depth": 0
        }
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Step {iteration}] Current Expression: {self.current_state['expression']}")
            
            # Use Theorist to propose 3 NEXT steps from the current state
            # We pack the current state into the problem context
            context_to_pass = {
                "current_state": self.current_state,
                "derivation_path": self.history,
                "recent_failures": dict(list(self.tree_log.items())[-3:]) if self.tree_log else {}
            }
            
            proposals = self.theorist.solve(self.problem, context=context_to_pass)
            if not isinstance(proposals, list):
                if isinstance(proposals, dict) and 'error' in proposals:
                    print(f"Agent error: {proposals}")
                    return
                proposals = [proposals]

            step_found = False
            for index, step in enumerate(proposals):
                print(f"\n>>>> [Attempt {index+1}] Action: {step.get('action_type', 'Transform')} <<<<")
                print(f"[Theorist] Logic: {step.get('logic', '')}")
                
                # Verify Step Equivalence: Next_State numerical value should equal Current_State numerical value
                print(f"[Orchestrator] Verifying mathematical equivalence of step...")
                
                # Numerical check: evaluate both expressions
                try:
                    # Parent expression value
                    parent_expr = self._clean_math_expr(self.current_state['expression'])
                    # If it's a raw integrand (like in the first step), wrap it
                    if "Integral" not in parent_expr:
                        bounds = self.problem.get('bounds', '[0, oo]').strip('[]').split(',')
                        parent_expr = f"Integral({parent_expr}, (x, {bounds[0]}, {bounds[1]}))"
                    
                    action = step.get('action_type', '').lower()
                    child_expr = self._clean_math_expr(step.get('sympy_code', ''))

                    if "differentiation" in action:
                        print(f"[Orchestrator] Differentiation step detected. Comparing I'(a) vs Child...")
                        # Assume differentiating w.r.t 'a' (default parameter)
                        parent_val = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
                    else:
                        parent_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
                    
                    child_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
                    
                    if parent_val is not None and child_val is not None:
                        diff = abs(parent_val - child_val)
                        print(f"[Orchestrator] Parent: {parent_val}, Child: {child_val}, Diff: {diff}")
                        if diff > 1e-4:
                            print(f"[Failure] Step invalid: numerical mismatch ({diff})")
                            continue
                    else:
                        if parent_val is None:
                            print(f"[Failure] Oracle could not evaluate parent/derivative: {parent_expr}")
                        if child_val is None:
                            print(f"[Failure] Oracle could not evaluate child: {child_expr}")
                        continue
                except Exception as e:
                    print(f"[Failure] Equivalence check failed with exception: {e}")
                    continue
                
                # Check for loops (if this expression was already reached earlier)
                if any(h.get('sympy_code') == step.get('sympy_code') for h in self.history):
                    print(f"[Failure] Infinite loop detected. Rejecting proposal.")
                    continue
                
                # If terminal, verify the final result against the Ground Truth Oracle
                if step.get('is_terminal'):
                    print(f"[Orchestrator] Terminal step reached. Verifying final result...")
                    oracle_val = self.oracle.evaluate_ground_truth(self.problem)
                    
                    # Coder generates execution script for the final expression
                    # (In a real system, Coder would solve the resulting standard integral)
                    implementation = self.coder.generate_implementation(step, oracle_val)
                    script_path = f"eval_step_{iteration}_{index+1}.py"
                    with open(script_path, "w", encoding='utf-8') as f:
                        f.write(implementation.get("python_script", ""))
                    
                    verification_result = self.verifier.verify(script_path, oracle_val)
                    
                    if verification_result.get("status") == "SUCCESS":
                        print(f"[Success] Logic chain completed! Residual: {verification_result.get('residual')}")
                        self.history.append(step)
                        self.finalize(step)
                        return
                    else:
                        print(f"[Failure] Terminal verification failed: {verification_result.get('verdict')}")
                else:
                    # Non-terminal step: update state and move forward
                    print(f"[Success] Step validated. Moving to next expression.")
                    self.current_state = {
                        "expression": step.get('sympy_code'),
                        "latex": step.get('intermediate_expression'),
                        "depth": iteration
                    }
                    self.history.append(step)
                    
                    # Log to tree log
                    attempt_id = len(self.tree_log) + 1
                    self.tree_log[f"Step_{attempt_id}"] = {
                        "from": parent_expr,
                        "to": step.get('sympy_code'),
                        "action": step.get('action_type'),
                        "logic": step.get('logic')
                    }
                    self._save_tree_log()
                    step_found = True
                    break # DFS-like exploration: take the first successful branch

            if not step_found:
                print(f"[Backtrack] No valid transformation found at this level. Restarting search.")
                self.state = "RETRY"
                # In a more advanced version, we would backtrack to the previous node
                continue

        print("\n[Safety] Hard cap of 10 iterations reached. All paths failed. Halting.")
        # Trigger report even on failure to summarize attempts
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", language=self.report_language)

    def finalize(self, result):
        print("\n--- Compiling Final Summary ---")
        # Extract LaTeX and analytical expressions
        print(f"Final Analytical Solution: {result.get('analytical_expression', 'Undetermined')}")
        
        # Trigger Reporter Agent for the full project paper
        self.reporter.generate_report(self.problem, self.tree_log, "thinking_process.txt", final_solution=result, language=self.report_language)

if __name__ == "__main__":
    problem = {
            "name": "Parametric Sinusoidal Decay Integral",
            "integrand": "f(x, a) = sin(a*x) / (x * (x**2 + 1))",
            "bounds": "[0, mp.inf]",
            "parameters": ["a=1", "a=2", "a=5"],
            "target": "Find the general closed-form solution as a function of parameter 'a' (a > 0).",
            "hint": "Consider partial fraction decomposition: 1/(x(x^2+1)) = 1/x - x/(x^2+1), or differentiation under the integral sign with respect to 'a'."
    }
    orchestrator = ResearchOrchestrator(problem, report_language="Chinese") # Example: Generate report in Chinese
    orchestrator.run()
