import sys
import os
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
        self.history = []

    def run(self):
        print(f"--- Initializing Research Loop for: {self.problem['name']} ---")
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Iteration {iteration}/{self.max_iterations}] State: {self.state}")
            
            # Step 2.1: Theorist proposes
            symbolic_proposal = self.theorist.solve(self.problem)
            print(f"[Theorist] Proposed Derivation: {symbolic_proposal['symbolic_derivation']}")
            
            # Step 2.2: Coder implements
            implementation = self.coder.generate_implementation(symbolic_proposal)
            with open("eval_step.py", "w") as f:
                f.write(implementation["python_script"])
            
            # Step 2.3: Verifier executes and checks
            print(f"[Orchestrator] Evaluating Numerical Oracle for {self.problem['name']}...")
            oracle_val = self.oracle.evaluate_ground_truth(self.problem)
            print(f"[Orchestrator] Oracle value: {oracle_val}")
            verification_result = self.verifier.verify("eval_step.py", oracle_val)
            
            if verification_result["status"] == "SUCCESS":
                print(f"[Success] Convergence achieved! Residual: {verification_result['residual']}")
                self.finalize(symbolic_proposal)
                return
            else:
                print(f"[Failure] Critique: {verification_result['critique']}")
                self.state = "FEEDBACK"
                continue

        print("\n[Safety] Hard cap of 10 iterations reached. Halting.")

    def finalize(self, result):
        print("\n--- Compiling Final Summary ---")
        # Extract LaTeX and analytical expressions
        print("Final Analytical Solution: ...")
        # Generate LaTeX summary...

if __name__ == "__main__":
    problem = {
            "name": "Cosmic String Radiation Integral (1D Slice)", # 补上缺失的 name 字段
            "integrand": "f(t, N) = (1 - (-1)**N * cos(N * pi * t)) / (1 - t**2)",
            "bounds": "[-1, 1]",
            "parameters": ["N (integer, evaluate for N=1, 2, 3, 5, 10)"],
            "target": "Find a closed-form analytical solution or a highly efficient series representation in terms of N. Specifically address the 0/0 singularity at t = +/- 1.",
            "hint": "Consider using differentiation under the integral sign with respect to a dummy parameter, or expanding the kernel using orthogonal polynomials."
    }
    orchestrator = ResearchOrchestrator(problem)
    orchestrator.run()
