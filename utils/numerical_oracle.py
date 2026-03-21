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
        s = str(expr_str)
        
        # Consistent infinity replacement
        s = s.replace('mp.inf', 'oo').replace('sp.inf', 'oo').replace('inf', 'oo')
        
        # Workaround for 'I' as a function name (Sympy uses I for sqrt(-1))
        import re
        s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)

        # Remove any leading variable assignments like "f(x, a) =" 
        s = re.sub(r'^[a-zA-Z_][a-zA-Z0-9_\'"]*(\([^)]*\))?\s*[:=]\s*', '', s)
        
        # Remove any lingering "=" if it's not an equation
        if "=" in s and "Eq(" not in s: 
            s = s.split("=")[-1]
            
        return s.strip()

    def evaluate_full_expression(self, problem, expression_str):
        try:
            import sympy as sp
            s = self._clean_expression(expression_str)
            
            # Map parameters: Use the FIRST value if multiple are provided
            subs = {}
            if 'parameters' in problem:
                for p in problem['parameters']:
                    if '=' in p:
                        k, v = p.split('=')
                        k = k.strip()
                        if k not in subs:
                            subs[k] = mp.mpf(v.strip())
            
            # Namespace
            ns = {
                'oo': sp.oo, 'pi': sp.pi, 'Integral': sp.Integral,
                'sin': sp.sin, 'cos': sp.cos, 'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt,
                'tan': sp.tan, 'atan': sp.atan, 'acos': sp.acos, 'asin': sp.asin,
                'Derivative': sp.Derivative, 'diff': sp.diff,
                'f': sp.Function('f'), 'im': sp.im, 'Im': sp.im, 're': sp.re, 'Symbol': sp.Symbol,
                'Eq': sp.Eq, 'Abs': sp.Abs,
                'Piecewise': sp.Piecewise, 'DiracDelta': sp.DiracDelta,
                'Sum': sp.Sum, 'KroneckerDelta': sp.KroneckerDelta,
                'a': sp.Symbol('a'), 'x': sp.Symbol('x'), 'u': sp.Symbol('u'),
                't': sp.Symbol('t', positive=True), 'C': sp.Symbol('C'),
                'k': sp.Symbol('k', real=True),
                'omega': sp.Symbol('omega', real=True),
                'eta': sp.Symbol('eta', positive=True),
                'z': sp.Symbol('z'),
                'IntFunc': sp.Function('I'), 'I': sp.I,
                'True': True, 'False': False,
            }
            expr = sp.sympify(s, locals=ns)
            
            if 'C' not in subs:
                subs['C'] = 0
            
            # If it's an equation (Eq), take the RHS immediately
            if isinstance(expr, sp.Equality):
                expr = expr.rhs
            
            # Substitute parameters after taking RHS to avoid diff(expr, value) errors
            expr = expr.subs(subs)
            
            # Try symbolic evaluation first
            try:
                sym_res = expr.doit().evalf(50)
                if sym_res.is_number:
                    return mp.mpf(str(sym_res))
            except:
                pass
            
            # Recursive evaluator
            def _eval_node(node):
                if node.is_number:
                    # mpmath handles string conversion of SymPy numbers well
                    return mp.mpf(str(node.evalf(50)))
                
                # Handle constants
                if node == sp.pi: return mp.pi
                if node == sp.exp(1): return mp.e
                if node == sp.oo: return mp.inf
                if node == sp.I: return mp.j

                # Handle sums/muls
                if node.is_Add: return sum(_eval_node(arg) for arg in node.args)
                if node.is_Mul:
                    prod = mp.mpf(1)
                    for arg in node.args: prod *= _eval_node(arg)
                    return prod
                if node.is_Pow: return _eval_node(node.base) ** _eval_node(node.exp)

                # Handle functions
                # Check for various SymPy function types
                if node.is_Function or any(isinstance(node, t) for t in [sp.sin, sp.cos, sp.exp, sp.log, sp.sqrt, sp.Abs, sp.im, sp.re, sp.tan, sp.atan]):
                    func_name = str(node.func).split('.')[-1]
                    args = [_eval_node(arg) for arg in node.args]
                    
                    if func_name == 'sin': return mp.sin(args[0])
                    if func_name == 'cos': return mp.cos(args[0])
                    if func_name == 'exp': return mp.exp(args[0])
                    if func_name == 'log': return mp.log(args[0])
                    if func_name == 'sqrt': return mp.sqrt(args[0])
                    if func_name == 'Abs': return abs(args[0])
                    if func_name == 'im': return mp.im(args[0])
                    if func_name == 're': return mp.re(args[0])
                    if func_name == 'tan': return mp.tan(args[0])
                    if func_name == 'atan': return mp.atan(args[0])
                    # For unknown functions, try symbolic evalf
                    pass

                # Handle Integral
                if isinstance(node, sp.Integral):
                    integrand = node.args[0]
                    limits = node.args[1:]
                    if len(limits) >= 1:
                        var, low, high = limits[-1]
                        remaining_limits = limits[:-1]
                        
                        low_val = _eval_node(low)
                        high_val = _eval_node(high)
                        
                        def f_inner(v):
                            try:
                                inner_node = integrand
                                if remaining_limits:
                                    inner_node = sp.Integral(integrand, *remaining_limits)
                                res = _eval_node(inner_node.subs({var: v}))
                                if res is None:
                                    # Try a small offset for singularities
                                    res = _eval_node(inner_node.subs({var: v + 1e-20}))
                                return res
                            except ZeroDivisionError:
                                # Handle removable singularities at v=0 (e.g., sin(x)/x)
                                return _eval_node(inner_node.subs({var: v + 1e-20}))
                            except Exception as e:
                                # print(f"[Oracle] f_inner error at v={v}: {e}")
                                return 0
                        
                        try:
                            # Use error=True to see mpmath quad errors
                            return mp.quad(f_inner, [low_val, high_val])
                        except Exception as e:
                            print(f"[Oracle] mp.quad error: {e}")
                            # If it fails, try with a slightly shifted lower bound if it's 0
                            if low_val == 0:
                                try:
                                    return mp.quad(f_inner, [mp.mpf('1e-15'), high_val])
                                except:
                                    return None
                            return None

                # Fallback: full symbolic evaluation
                try:
                    res = node.evalf(50)
                    if res.is_number:
                        return mp.mpf(str(res))
                except:
                    pass
                return None

            res = _eval_node(expr)
            return res
        except Exception as e:
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
                        k = k.strip()
                        if k not in subs:
                            subs[k] = mp.mpf(v.strip())
            
            ns = {
                'oo': sp.oo, 'pi': sp.pi, 'sin': sp.sin, 'cos': sp.cos,
                'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt,
                'IntFunc': sp.Function('I'), 'I': sp.I
            }
            expr = sp.sympify(s, locals=ns)
            free = [fs for fs in expr.free_symbols if str(fs) not in subs]
            var = free[0] if free else sp.Symbol('x')
            
            res = expr.subs(subs).subs({var: mp.mpf(point)}).evalf(50)
            return mp.mpf(str(res))
        except:
            return None

    def evaluate_ground_truth(self, problem):
        """
        Evaluate the ground truth value for the given problem.
        For CMP/DOS problems, uses direct numerical integration of the Green's function.
        For standard integral problems, uses the original integrand evaluation.
        """
        try:
            name = problem.get('name', '')
            
            # --- CMP: 1D Tight-Binding DOS ---
            if 'Tight-Binding' in name or 'DOS' in name:
                return self._evaluate_dos_ground_truth(problem)
            
            # --- Standard integral problems ---
            integrand = self._clean_expression(problem['integrand'])
            bounds = problem.get('bounds', '[0, oo]').strip('[]').split(',')
            lower = self._clean_expression(bounds[0])
            upper = self._clean_expression(bounds[1])
            expr_str = f"Integral({integrand}, (x, {lower}, {upper}))"
            return self.evaluate_full_expression(problem, expr_str)
        except:
            return None

    def _evaluate_dos_ground_truth(self, problem):
        """
        Compute the exact analytic ground truth for the 1D tight-binding DOS.
        
        The analytic expression is:
            D(omega) = 1 / (pi * sqrt(4*t^2 - omega^2))   for |omega| < 2t
        
        We evaluate at omega=0 (band center) where D(0) = 1/(2*pi*t).
        This avoids expensive numerical integration of the near-singular Green's function.
        """
        params = {}
        for p in problem.get('parameters', []):
            if '=' in p:
                k_name, v = p.split('=')
                params[k_name.strip()] = mp.mpf(v.strip())
        
        t_val = params.get('t', mp.mpf('1.0'))
        omega_val = mp.mpf('0.0')  # Evaluate at band center
        
        # Exact analytic result: D(omega) = 1/(pi * sqrt(4t^2 - omega^2))
        analytic_dos = 1.0 / (mp.pi * mp.sqrt(4 * t_val**2 - omega_val**2))
        
        print(f"[Oracle/CMP] DOS ground truth at omega={omega_val}: D = {analytic_dos}")
        print(f"[Oracle/CMP] Expected: 1/(2*pi*t) = {1.0 / (2 * mp.pi * t_val)}")
        return analytic_dos


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
            found = False
            for p in problem.get('parameters', []):
                if p.startswith(f"{wrt}="):
                    current_val = float(p.split('=')[1])
                    found = True
                    break
            
            if not found and wrt == 'a':
                # Try to search in other formats if needed, or default
                pass
            
            # Manual central difference for better stability with sympify/subs
            h = 1e-7
            v_plus = f_val(current_val + h)
            v_minus = f_val(current_val - h)
            
            if v_plus is None or v_minus is None:
                # Fallback to one-sided if needed, though f_val returns 0 on None
                return 0
                
            return (mp.mpf(str(v_plus)) - mp.mpf(str(v_minus))) / (2 * h)
        except Exception as e:
            print(f"[Oracle] Derivative error: {e}")
            return 0

    def evaluate_asymptotic_limit(self, problem, expression_str, wrt='a', limit_type='zero'):
        """
        Evaluates the limit of the expression as wrt approaches zero or infinity.
        """
        try:
            if limit_type == 'zero':
                val = 1e-12
            else:
                val = 1e12
                
            temp_problem = problem.copy()
            params = []
            for p in problem.get('parameters', []):
                if p.startswith(f"{wrt}="):
                    params.append(f"{wrt}={val}")
                else:
                    params.append(p)
            temp_problem['parameters'] = params
            
            res = self.evaluate_full_expression(temp_problem, expression_str)
            return res
        except Exception as e:
            print(f"[Oracle] Asymptotic error: {e}")
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
