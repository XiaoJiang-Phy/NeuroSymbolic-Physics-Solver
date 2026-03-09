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

    def _clean_expression(self, expr_str):
        if not expr_str: return ""
        s = str(expr_str).replace('mp.inf', 'inf').replace('sp.inf', 'inf').replace('oo', 'inf')
        
        # Workaround for 'I' as a function name (Sympy uses I for sqrt(-1))
        # Replace 'I(' with 'IntFunc(' if it's not preceded by a letter (avoiding things like 'sinI(')
        import re
        s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)

        # Remove any leading variable assignments
        import re
        s = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_\'"]*(\([^)]*\))?\s*[:=]\s*', '', s)
        # Final cleanup of prefixes
        if "=" in s and "(" not in s.split("=")[0]: s = s.split("=")[-1]
        return s.strip()

    def evaluate_full_expression(self, problem, expression_str):
        try:
            import sympy as sp
            s = self._clean_expression(expression_str)
            
            # Map parameters
            subs = {}
            if 'parameters' in problem:
                for p in problem['parameters']:
                    if '=' in p:
                        k, v = p.split('=')
                        subs[k.strip()] = mp.mpf(v.strip())
            
            # Namespace
            ns = {
                'oo': sp.oo, 'inf': sp.oo, 'pi': sp.pi, 'Integral': sp.Integral,
                'sin': sp.sin, 'cos': sp.cos, 'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt,
                'tan': sp.tan, 'atan': sp.atan, 'Derivative': sp.Derivative, 'diff': sp.diff,
                'f': sp.Function('f'), 'im': sp.im, 're': sp.re, 'Symbol': sp.Symbol,
                'IntFunc': sp.Function('I'), 'I': sp.I
            }
            expr = sp.sympify(s, locals=ns)
            
            # If it's an equation (Eq), take the RHS to evaluate its numerical value
            if isinstance(expr, sp.Equality):
                expr = expr.rhs
            
            # Try symbolic evaluation first
            try:
                # doit() evaluates integrals/derivatives if possible
                sym_res = expr.doit().subs(subs).evalf(50)
                if sym_res.is_number:
                    return mp.mpf(str(sym_res))
            except:
                pass

            # Recursive evaluator to handle nodes mpmath-style
            def _eval_node(node):
                if node.is_number:
                    return mp.mpf(str(node.evalf(50)))
                
                # Handle constants pi/e
                if node == sp.pi: return mp.pi
                if node == sp.exp(1): return mp.e

                # Handle sums/muls
                if node.is_Add: return sum(_eval_node(arg) for arg in node.args)
                if node.is_Mul:
                    prod = mp.mpf(1)
                    for arg in node.args: prod *= _eval_node(arg)
                    return prod
                if node.is_Pow: return _eval_node(node.base) ** _eval_node(node.exp)

                # Handle Integral(f(x), (x, a, b))
                if isinstance(node, sp.Integral):
                    integrand = node.args[0]
                    limits = node.args[1:]
                    if len(limits) == 1:
                        var, low, high = limits[0]
                        # Substitutions for limits
                        low_val = _eval_node(low.subs(subs))
                        high_val = _eval_node(high.subs(subs))
                        
                        # Use mpmath.quad for numerical integration
                        # We lambdify the integrand with mpmath functions
                        f_num = sp.lambdify(var, integrand.subs(subs), modules='mpmath')
                        # tanh-sinh is robust for infinite/singular integrals
                        return mp.quad(f_num, [low_val, high_val])

                # Fallback to evalf on the substituted node
                res = node.subs(subs).evalf(50)
                if res.is_number:
                    return mp.mpf(str(res))
                return None

            return _eval_node(expr)
        except Exception as e:
            print(f"[Oracle] Parse/Eval error: {e} for {expression_str}")
            return None

    def evaluate_integrand(self, problem, point):
        try:
            import sympy as sp
            s = self._clean_expression(problem['integrand'])
            subs = {}
            if 'parameters' in problem:
                for p in problem['parameters']:
                    if '=' in p:
                        k, v = p.split('=')
                        subs[k.strip()] = mp.mpf(v.strip())
            
            ns = {
                'oo': sp.oo, 'inf': sp.oo, 'pi': sp.pi, 'sin': sp.sin, 'cos': sp.cos,
                'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt,
                'IntFunc': sp.Function('I'), 'I': sp.I
            }
            expr = sp.sympify(s, locals=ns)
            # Find the free symbol that is not a parameter
            free = [fs for fs in expr.free_symbols if str(fs) not in subs]
            var = free[0] if free else sp.Symbol('x')
            
            res = expr.subs(subs).subs({var: mp.mpf(point)}).evalf(50)
            return mp.mpf(str(res))
        except:
            return None

    def evaluate_ground_truth(self, problem):
        try:
            integrand = self._clean_expression(problem['integrand'])
            bounds = problem.get('bounds', '[0, inf]').strip('[]').split(',')
            lower = self._clean_expression(bounds[0])
            upper = self._clean_expression(bounds[1])
            expr_str = f"Integral({integrand}, (x, {lower}, {upper}))"
            return self.evaluate_full_expression(problem, expr_str)
        except:
            return None

    def evaluate_derivative(self, problem, expression_str, wrt='a'):
        """
        Numerically differentiates the expression with respect to the parameter.
        """
        try:
            # We want to evaluate d/d(wrt) of expression_str
            # We'll create a function f(val) where val is the value of parameter 'wrt'
            def f_val(val):
                # Temporary problem with updated parameter
                temp_problem = problem.copy()
                params = []
                for p in problem.get('parameters', []):
                    if p.startswith(f"{wrt}="):
                        params.append(f"{wrt}={val}")
                    else:
                        params.append(p)
                temp_problem['parameters'] = params
                res = self.evaluate_full_expression(temp_problem, expression_str)
                return res if res is not None else 0
            
            # Find the current value of the parameter
            current_val = 1.0
            for p in problem.get('parameters', []):
                if p.startswith(f"{wrt}="):
                    current_val = float(p.split('=')[1])
            
            # mpmath.diff handles numeric differentiation
            return mp.diff(f_val, current_val)
        except Exception as e:
            print(f"[Oracle] Derivative error: {e}")
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
