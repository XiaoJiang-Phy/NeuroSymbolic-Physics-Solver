import sympy as sp
from utils.feynman_translator import get_feynman_translator

def test_feynman_translator():
    translator = get_feynman_translator()
    
    # 1. Test bare propagator
    epsilon_k = sp.Symbol('epsilon_k', real=True)
    G0 = translator.get_bare_propagator(translator.k, translator.omega, epsilon_k, statistics='fermion')
    assert G0 == 1 / (translator.omega - epsilon_k)
    
    # 2. Test first-order self energy (Fermion Tadpole)
    vertex = translator.V
    loop_vars = (translator.q, -sp.oo, sp.oo)
    sigma = translator.first_order_self_energy(G0, vertex, loop_vars, statistics='fermion')
    # Should yield Integral(-V * G0, (q, -oo, oo))
    expected_sigma = sp.Integral(-vertex * G0, (translator.q, -sp.oo, sp.oo))
    assert sigma == expected_sigma
    
    # 3. Test Gap equation
    F_k = sp.Function('F')(translator.k, translator.omega) # anomalous Green's func
    loop_bounds = [(translator.omega, -sp.oo, sp.oo), (translator.k, -sp.pi, sp.pi)]
    interaction = -translator.V
    gap_eq = translator.self_consistent_gap_equation(translator.Delta, interaction, F_k, loop_bounds)
    
    # Right-hand side should be interaction * Integral(Integral(F_k, k_bound), omega_bound)
    expected_integral = sp.Integral(sp.Integral(F_k, (translator.k, -sp.pi, sp.pi)), (translator.omega, -sp.oo, sp.oo))
    expected_rhs = interaction * expected_integral
    assert gap_eq == sp.Eq(translator.Delta, expected_rhs)
    
    print("Feynman Translator Tests Passed!")

if __name__ == "__main__":
    test_feynman_translator()
