import os
import json
from agents.reporter_agent import ReporterAgent

def test_tree_visualization():
    problem = {
        "name": "Parametric Sinusoidal Decay Integral",
        "integrand": "f(x, a) = sin(a*x) / (x * (x**2 + 1))",
        "bounds": "[0, mp.inf]",
        "parameters": ["a=1", "a=2", "a=5"],
        "target": "Find the general closed-form solution as a function of parameter 'a' (a > 0)."
    }

    log_path = "tree_log.json"
    with open(log_path, "r", encoding='utf-8') as f:
        tree_log = json.load(f)

    reporter = ReporterAgent()
    thinking_path = "thinking_process.txt"
    final_solution = {
        "path_type": "Analytical_Derivation",
        "analytical_expression": "I(a) = (pi/2) * (1 - exp(-a))",
        "sympy_code": "pi/2 * (1 - exp(-a))"
    }

    print("--- Testing Real Reasoning Tree Visualization ---")
    reporter.generate_report(problem, tree_log, thinking_path, final_solution=final_solution, language="Chinese")
    print("--- Done ---")

if __name__ == "__main__":
    test_tree_visualization()
