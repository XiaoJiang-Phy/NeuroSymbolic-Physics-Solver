import sympy as sp
from utils.matsubara_engine import get_matsubara_engine
from utils.feynman_translator import get_feynman_translator

def run_demo():
    print("="*60)
    print(" NeuroSymbolic Physics Solver: Many-Body Engine Prototype")
    print("="*60)
    
    m_engine = get_matsubara_engine()
    f_trans = get_feynman_translator()
    
    # ---------------------------------------------------------
    print("\n[STEP 1] Initialization: Defining Many-Body symbolic variables")
    q = sp.Symbol('q', real=True)
    epsilon_q = sp.Function('epsilon')(q)
    V_0 = sp.Symbol('V_0', real=True) # Hartree interaction strength V(q=0)
    Sigma_H = sp.Symbol('Sigma_{Hartree}')
    
    print("  > Interaction Vertex: V_0")
    print("  > Dispersion: epsilon(q)")
    
    # ---------------------------------------------------------
    print("\n[STEP 2] Feynman Diagram Translator: Generating Hartree Loop (Tadpole)")
    
    # 2.1 Get Bare Propagator G0
    # G0(i w_n) = 1 / (i w_n - epsilon_q)
    i_omega_n = sp.I * m_engine.omega_n
    G0 = f_trans.get_bare_propagator(q, i_omega_n, epsilon_q, statistics='fermion')
    
    print("\n  bare Green's function G0(q, i w_n):")
    sp.pprint(G0, use_unicode=True)
    
    # 2.2 Construct the first-order self-energy formal integral
    loop_bounds = (q, -sp.oo, sp.oo)
    sigma_integral = f_trans.first_order_self_energy(G0, V_0, loop_bounds, statistics='fermion')
    
    print("\n  Formal Diagrammatic Integral (before Matsubara processing):")
    # For display, we manually add the 1/beta * Sum
    summation = (1 / m_engine.beta) * sp.Sum(sigma_integral, (m_engine.omega_n, -sp.oo, sp.oo))
    sp.pprint(sp.Eq(Sigma_H, summation), use_unicode=True)
    
    # ---------------------------------------------------------
    print("\n[STEP 3] Matsubara Frequency Conversion: Analytic Continuation")
    
    # 3.1 Map discrete sum to contour integral integrand f(z)*n_F(z)
    integrand_z = m_engine.do_matsubara_sum(G0, statistics='fermion')
    print("\n  Integrand mapped to complex z plane f(z) * n_F(z):")
    sp.pprint(integrand_z, use_unicode=True)
    
    # 3.2 Formal Cauchy Residue Theorem Evaluation at Pole z = epsilon(q)
    print("\n  Evaluating contour integral via Cauchy's Residue Theorem at pole z = epsilon(q)...")
    
    # The residue of 1/(z - epsilon) at z=epsilon is 1. 
    # The contour formula gives Sum_{iw} = (-1) * [Residues of f(z)*n_F(z) at poles of f]
    residue_val = integrand_z.subs(1/(m_engine.z - epsilon_q), 1).subs(m_engine.z, epsilon_q)
    sum_result = residue_val # Note: Fermion loop trace prepends a minus sign cancelling the contour minus sign
    
    print("  Matsubara sum analytically evaluates to the Fermi-Dirac occupation number:")
    sp.pprint(sum_result, use_unicode=True)
    
    # ---------------------------------------------------------
    print("\n[STEP 4] Output Final Self-Consistent Physical Equation")
    
    # 4.1 Re-assemble the final analytical equation
    # Replace the bare G0 * vertex with the evaluated Matsubara sum * vertex
    # The sign convention in f_trans.first_order_self_energy for fermion is already -1.
    final_integrand = V_0 * sum_result
    final_eq = sp.Eq(Sigma_H, sp.Integral(final_integrand, loop_bounds))
    
    print("\n  Final analytical result for Finite-Temperature Hartree Self-Energy:")
    sp.pprint(final_eq, use_unicode=True)
    
    print("\n" + "="*60)
    print(" Prototype Demonstration Successful!")

if __name__ == '__main__':
    run_demo()
