from mpmath import mp

# Set global precision to 100 dps for internal Oracle robustness
mp.dps = 100

class NumericalOracle:
    """
    Implements a 50-dps mpmath baseline for ground truth calculations.
    Refactored to handle baseline calibration integral: cos(x) / sqrt(1 - x^2)
    """
    def __init__(self):
        pass

    def evaluate_integrand(self, problem, point):
        """
        Evaluates the parsed integrand at a specific point for Early Exit verification.
        """
        try:
            integrand_str = problem['integrand']
            # Robust parsing for multi-line or assigned expressions
            if "integrand" in integrand_str and "=" in integrand_str:
                lines = integrand_str.splitlines()
                for line in reversed(lines):
                    if "=" in line and ("integrand" in line or "expr" in line):
                        expr_str = line.split("=")[-1].strip()
                        break
            elif '=' in integrand_str:
                expr_str = integrand_str.split('=')[1].strip()
            else:
                expr_str = integrand_str.strip()

            ctx = {
                'cos': mp.cos, 'sin': mp.sin, 'sqrt': mp.sqrt, 
                'pi': mp.pi, 'exp': mp.exp, 'log': mp.log,
                'inf': mp.inf, 'oo': mp.inf,
                'I': 1j, 'j': 1j,
                'sp': mp, 'sympy': mp,
                'Integral': mp.quad,
                'Derivative': mp.diff
            }
            
            if 'parameters' in problem and problem['parameters']:
                first_param = problem['parameters'][0]
                if '=' in first_param:
                    name, val = first_param.split('=')
                    ctx[name.strip()] = float(val.strip())
            
            f = lambda x: eval(expr_str, {"__builtins__": {}}, {**ctx, 't': x, 'x': x, 'z': x})
            return f(point)
        except Exception as e:
            print(f"[Oracle] Error evaluating point: {e}")
            return None

    def evaluate_ground_truth(self, problem):
        """
        Numerically evaluates the integral specified in the problem definition.
        Handles endpoints robustly using mpmath.quad.
        """
        try:
            # Simple parsing of the integrand string
            # Expected format: "f(t, N) = (1 - (-1)**N * cos(N * pi * t)) / (1 - t**2)"
            # Or just the expression.
            integrand_str = problem['integrand']
            # Robust parsing for multi-line or assigned expressions
            if "integrand" in integrand_str and "=" in integrand_str:
                lines = integrand_str.splitlines()
                for line in reversed(lines):
                    if "=" in line and ("integrand" in line or "expr" in line):
                        expr_str = line.split("=")[-1].strip()
                        break
            elif '=' in integrand_str:
                expr_str = integrand_str.split('=')[1].strip()
            else:
                expr_str = integrand_str.strip()

            # For the MVP, we assume a single variable 't' or 'x'
            # and parameters are handled. For N=1 (baseline for first run).
            # In a real system, we'd parse parameters from problem['parameters']
            
            # Mapping common math functions to mpmath
            ctx = {
                'cos': mp.cos, 'sin': mp.sin, 'sqrt': mp.sqrt, 
                'pi': mp.pi, 'exp': mp.exp, 'log': mp.log,
                'inf': mp.inf, 'oo': mp.inf,
                'I': 1j, 'j': 1j,
                'sp': mp, 'sympy': mp
            }
            
            # Extract parameter from problem['parameters']
            # We use ONLY the first one to stay consistent with the Coder's instructions
            if 'parameters' in problem and problem['parameters']:
                first_param = problem['parameters'][0]
                if '=' in first_param:
                    name, val = first_param.split('=')
                    ctx[name.strip()] = float(val.strip())
            
            f = lambda x: eval(expr_str, {"__builtins__": {}}, {**ctx, 't': x, 'x': x, 'z': x})
            
            bounds = problem['bounds']
            # Parse bounds if they are string like "[0, mp.inf]"
            if isinstance(bounds, str):
                import re
                # Handle special keywords like mp.inf, inf, oo
                clean_bounds = bounds.replace('mp.inf', 'inf').replace('oo', 'inf').strip('[]')
                parts = [p.strip() for p in clean_bounds.split(',')]
                actual_bounds = []
                for p in parts:
                    if 'inf' in p.lower():
                        actual_bounds.append(mp.inf if '-' not in p else -mp.inf)
                    else:
                        actual_bounds.append(float(p))
                # For infinite ranges, add intermediate points to help mpmath sample better
                if any(mp.isinf(b) for b in actual_bounds):
                    new_bounds = [actual_bounds[0]]
                    if actual_bounds[0] < 1 < actual_bounds[-1]: new_bounds.append(1)
                    if actual_bounds[0] < 10 < actual_bounds[-1]: new_bounds.append(10)
                    if actual_bounds[0] < 100 < actual_bounds[-1]: new_bounds.append(100)
                    new_bounds.append(actual_bounds[-1])
                    actual_bounds = new_bounds
                bounds = actual_bounds
                
            val = mp.quad(f, bounds, maxdegree=12)
            return val
        except Exception as e:
            print(f"[Oracle] Error evaluating ground truth: {e}")
            return None

def get_oracle():
    return NumericalOracle()

if __name__ == "__main__":
    oracle = get_oracle()
    problem = {
        "integrand": "sin(a*x) / (x * (x**2 + 1))",
        "bounds": "[0, oo]",
        "parameters": ["a=1"]
    }
    result = oracle.evaluate_ground_truth(problem)
    print(f"Numerical result (a=1): {result}")
    
    # Analytical: pi/2 * (1 - exp(-1))
    analytical = mp.pi/2 * (1 - mp.exp(-1))
    print(f"Analytical verify: {analytical}")
    print(f"Difference: {result - analytical}")
