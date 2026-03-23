import sympy as sp
from utils.matsubara_engine import get_matsubara_engine

def test_matsubara_engine():
    engine = get_matsubara_engine()
    
    # Example 1: G(i omega_n) = 1 / (i omega_n - epsilon) (Fermion)
    epsilon = sp.Symbol('epsilon', real=True)
    expr = 1 / (sp.I * engine.omega_n - epsilon)
    
    continuous_integrand = engine.do_matsubara_sum(expr, statistics='fermion')
    
    # It should become 1/(z - epsilon) * 1/(exp(beta*z) + 1)
    expected_continuos = (1 / (engine.z - epsilon)) * (1 / (sp.exp(engine.beta * engine.z) + 1))
    
    # sp.simplify might not fully pull standard mathematical equalities depending on assumptions,
    # but exact substitution should match.
    diff = sp.simplify(continuous_integrand - expected_continuos)
    assert diff == 0, f"Fermion analytic continuation mismatch. Got: {continuous_integrand}"
    
    # Retarded Green's function (z -> omega + i eta)
    retarded, advanced = engine.analytic_continuation(1 / (engine.z - epsilon))
    expected_retarded = 1 / (engine.omega + sp.I * engine.eta - epsilon)
    assert retarded == expected_retarded, "Retarded function mismatch"
    
    print("Matsubara Engine Tests Passed!")

if __name__ == "__main__":
    test_matsubara_engine()
