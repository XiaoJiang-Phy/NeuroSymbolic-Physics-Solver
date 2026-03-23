import sympy as sp
from typing import Tuple

class FeynmanTranslator:
    """
    Phase 3.2: Feynman Diagram Translator (Diagrammatic Reasoning)
    Translates Feynman Rules into symbolic self-energy integrals and self-consistent Gap equations.
    """
    def __init__(self):
        # Momenta and frequencies
        self.k = sp.Symbol('k', real=True) # External momentum
        self.q = sp.Symbol('q', real=True) # Loop momentum
        self.omega = sp.Symbol('omega', complex=True) # Frequency
        self.nu = sp.Symbol('nu', complex=True) # Loop frequency (could be Matsubara)
        
        # Interaction couplings
        self.g = sp.Symbol('g', real=True)
        self.V = sp.Symbol('V', real=True)
        self.Delta = sp.Symbol('Delta', real=True) # Gap parameter

    def get_bare_propagator(self, momentum_var: sp.Symbol, freq_var: sp.Symbol, dispersion: sp.Expr, statistics: str = 'fermion') -> sp.Expr:
        """
        Generates the standard bare Green's function G_0(k, omega)
        fermion: 1 / (omega - epsilon_k)
        boson: 2*epsilon / (omega^2 - epsilon_k^2)
        """
        if statistics == 'fermion':
            return 1 / (freq_var - dispersion)
        elif statistics == 'boson':
            # Approximation/formualtion often depends on conventions. Defaulting to standard bosonic form.
            return 2 * dispersion / (freq_var**2 - dispersion**2)
        else:
            raise ValueError("Statistics must be 'fermion' or 'boson'")

    def first_order_self_energy(self, G_loop: sp.Expr, vertex: sp.Expr, loop_vars: Tuple[sp.Symbol, sp.Expr, sp.Expr], statistics: str = 'fermion') -> sp.Expr:
        """
        Generates the integral expression for first-order self-energy.
        Sigma = (+/-) \int \frac{d^d q}{(2\pi)^d} V(q) G(q)
        Where (+/-) gives -1 for Fermion loops.
        """
        sign = -1 if statistics == 'fermion' else 1
        integrand = sign * vertex * G_loop
        
        var, lower, upper = loop_vars
        return sp.Integral(integrand, (var, lower, upper))

    def self_consistent_gap_equation(self, order_parameter: sp.Symbol, interaction: sp.Expr, anomalous_greens_function: sp.Expr, loop_vars: list) -> sp.Expr:
        """
        Generates a self-consistent Gap equation.
        E.g., Delta = -V \int \frac{d^3 k}{(2\pi)^3} F(k, \omega)
        """
        integral = anomalous_greens_function
        # For multiple integrations (e.g. over momentum and Matsubara sum)
        for var_bounds in reversed(loop_vars):
            integral = sp.Integral(integral, var_bounds)
            
        return sp.Eq(order_parameter, interaction * integral)

def get_feynman_translator() -> FeynmanTranslator:
    return FeynmanTranslator()
