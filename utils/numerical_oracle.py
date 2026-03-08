from mpmath import mp

# Set global precision to 50 dps as requested
mp.dps = 50

class NumericalOracle:
    """
    Implements a 50-dps mpmath baseline for ground truth calculations.
    Refactored to handle baseline calibration integral: cos(x) / sqrt(1 - x^2)
    """
    def __init__(self):
        pass

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
            if '=' in integrand_str:
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
                'N': 1 # Default N=1 for first validation
            }
            
            # Replace ** with ^ or similar if needed, but Python uses **
            f = lambda x: eval(expr_str, {"__builtins__": None}, {**ctx, 't': x, 'x': x})
            
            bounds = problem['bounds']
            # Parse bounds if they are string like "[-1, 1]"
            if isinstance(bounds, str):
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", bounds)
                bounds = [float(n) for n in nums]
                
            val = mp.quad(f, bounds)
            return val
        except Exception as e:
            print(f"[Oracle] Error evaluating ground truth: {e}")
            return None

def get_oracle():
    return NumericalOracle()

if __name__ == "__main__":
    oracle = get_oracle()
    result = oracle.evaluate_ground_truth()
    print(f"Numerical result (50 dps): {result}")
    # Analytical verification: pi * J0(1)
    j0_1 = mp.besselj(0, 1)
    truth = mp.pi * j0_1
    print(f"Analytical verify (pi*J0(1)): {truth}")
    print(f"Difference: {result - truth}")
