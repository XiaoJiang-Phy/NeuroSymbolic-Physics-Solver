import os
import json
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

from agents.theorist_agent import TheoristAgent
from agents.coder_agent import CoderAgent
from agents.verifier_agent import VerifierAgent
from utils.numerical_oracle import get_oracle

class ResearchOrchestrator:
    def __init__(self, problem_definition):
        self.problem = problem_definition
        self.theorist = TheoristAgent()
        self.coder = CoderAgent()
        self.verifier = VerifierAgent()
        self.oracle = get_oracle()
        self.state = "INIT"
        self.max_iterations = 10
        self.log_path = "tree_log.json"
        self.tree_log = self._load_tree_log()
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

    def run(self):
        # Initialize/Clear thinking process log
        with open("thinking_process.txt", "w", encoding='utf-8') as f:
            f.write(f"Research Log for: {self.problem['name']}\n")
            f.write("="*50 + "\n")

        print(f"--- Initializing Research Loop for: {self.problem['name']} ---")
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Iteration {iteration}/{self.max_iterations}] State: {self.state}")
            
            # Step 2.1: Theorist proposes multiple (3) paths
            proposals = self.theorist.solve(self.problem, context=self.tree_log)
            if not isinstance(proposals, list):
                if isinstance(proposals, dict) and 'error' in proposals:
                    print(f"Agent error: {proposals}")
                    return
                proposals = [proposals]  # Fallback to list
            
            branch_succeeded = False
            for index, symbolic_proposal in enumerate(proposals):
                print(f"\n>>>> [Branch {index+1}] Proposed Path: {symbolic_proposal.get('path_type', 'Unknown')} <<<<")
                print(f"[Theorist] Derivation: {symbolic_proposal.get('symbolic_derivation', '')}")
                print(f"[Theorist] Confidence: {symbolic_proposal.get('success_probability', '')}")
                
                # Retrieve ground truth at t=0.999 for early point sampling checks
                # BUG FIX: Evaluate the NEW proposed integrand, not the original problem
                temp_problem = self.problem.copy()
                temp_problem['integrand'] = symbolic_proposal.get('sympy_code', self.problem['integrand'])
                oracle_point_val = self.oracle.evaluate_integrand(temp_problem, 0.999)
                
                # Step 2.2: Coder implements
                implementation = self.coder.generate_implementation(symbolic_proposal, oracle_point_val)
                script_path = f"eval_step_branch_{index+1}.py"
                with open(script_path, "w", encoding='utf-8') as f:
                    f.write(implementation.get("python_script", ""))
                
                # Step 2.3: Verifier executes and checks
                print(f"[Orchestrator] Evaluating Numerical Oracle for {self.problem['name']}...")
                oracle_val = self.oracle.evaluate_ground_truth(self.problem)
                print(f"[Orchestrator] Oracle value: {oracle_val}")
                verification_result = self.verifier.verify(script_path, oracle_val)
                
                if verification_result.get("status") == "SUCCESS":
                    print(f"[Success] Convergence achieved on Branch {index+1}! Residual: {verification_result.get('residual')}")
                    self.finalize(symbolic_proposal)
                    branch_succeeded = True
                    return  # Break completely upon success
                else:
                    # Capture exact mathematical verdict from Verifier
                    verdict = verification_result.get("verdict", verification_result.get("critique", "Failed Execution"))
                    print(f"[Failure] Branch {index+1} Critique: {verdict}")
                    
                    # Log the negative feedback for future iterations (TreeLog)
                    self.tree_log[f"Iteration_{iteration}_Branch_{index+1}"] = {
                        "problem_name": self.problem['name'],
                        "proposal": symbolic_proposal,
                        "verdict": verdict
                    }
                    self._save_tree_log()
                    
                    # Context Pruning (Critical): Completely delete the intermediate code
                    if os.path.exists(script_path):
                        os.remove(script_path)
            
            if not branch_succeeded:
                self.state = "FEEDBACK"
                continue

        print("\n[Safety] Hard cap of 10 iterations reached. All paths failed. Halting.")

    def finalize(self, result):
        print("\n--- Compiling Final Summary ---")
        # Extract LaTeX and analytical expressions
        print("Final Analytical Solution: ...")
        # Generate LaTeX summary...

if __name__ == "__main__":
    problem = {
            "name": "Parametric Sinusoidal Decay Integral",
            "integrand": "f(x, a) = sin(a*x) / (x * (x**2 + 1))",
            "bounds": "[0, mp.inf]",
            "parameters": ["a=1", "a=2", "a=5"],
            "target": "Find the general closed-form solution as a function of parameter 'a' (a > 0).",
            "hint": "Consider partial fraction decomposition: 1/(x(x^2+1)) = 1/x - x/(x^2+1), or differentiation under the integral sign with respect to 'a'."
    }
    orchestrator = ResearchOrchestrator(problem)
    orchestrator.run()
