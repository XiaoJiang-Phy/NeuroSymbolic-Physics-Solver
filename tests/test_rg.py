import sympy as sp
from utils.rg_operator import get_rg_operator

def test_rg_operator():
    rg = get_rg_operator()
    
    # 1. Test Mode Elimination Split
    k = sp.Symbol('k', real=True)
    Lambda = rg.Lambda
    
    expr = 1 / (k**2 + 1)
    integral = sp.Integral(expr, (k, 0, Lambda))
    
    slow, fast = rg.mode_elimination_split(integral, k)
    
    assert slow.limits == ((k, 0, Lambda / rg.b),)
    assert fast.limits == ((k, Lambda / rg.b, Lambda),)
    
    # 2. Test Apply Scaling
    # Let Action = Integral( k^2 phi_k phi_{-k} )
    # Scaling dimensions: k -> k/b (dim=-1), phi_k -> phi_k * b^(3/2) (dim=1.5)
    
    phi_k = sp.Symbol('phi_k')
    phi_minus_k = sp.Symbol('phi_minus_k')
    
    action_term = k**2 * phi_k * phi_minus_k
    scaling_dims = {
        k: -1,
        phi_k: sp.Rational(3, 2),
        phi_minus_k: sp.Rational(3, 2)
    }
    
    scaled_action = rg.apply_scaling(action_term, scaling_dims)
    # expected: (k/b)^2 * (phi_k * b^(1.5)) * (phi_minus_k * b^(1.5))
    #         = k^2 / b^2 * phi_k * phi_minus_k * b^3
    #         = b * k^2 * phi_k * phi_minus_k
    expected_action = rg.b * action_term
    
    # Simplify test
    assert sp.simplify(scaled_action - expected_action) == 0
    
    # 3. Test flow equation
    g = sp.Symbol('g', real=True)
    beta_val = -0.1 * g**2
    flow_eq = rg.flow_equation(g, beta_val)
    expected_flow = sp.Eq(sp.Derivative(g, rg.dl), beta_val)
    
    assert flow_eq == expected_flow
    
    print("RG Operator Tests Passed!")

if __name__ == "__main__":
    test_rg_operator()
