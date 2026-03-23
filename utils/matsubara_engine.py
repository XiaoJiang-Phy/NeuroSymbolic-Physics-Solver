import sympy as sp
from typing import Tuple, Union

class MatsubaraEngine:
    """
    Phase 3.1: Matsubara Frequency Conversion Engine
    Handles the analytical continuation from discrete Matsubara summations to 
    continuous frequency integrations using Cauchy's residue theorem.
    """
    def __init__(self):
        self.beta = sp.Symbol('beta', real=True, positive=True) # Inverse temperature
        self.omega_n = sp.Symbol('omega_n', real=True) # Matsubara frequency index
        self.z = sp.Symbol('z', complex=True)
        self.omega = sp.Symbol('omega', real=True)
        self.eta = sp.Symbol('eta', real=True, positive=True)

    def do_matsubara_sum(self, F_i_omega_n: sp.Expr, statistics: str = 'fermion') -> sp.Expr:
        """
        Transforms a discrete Matsubara sum (1/beta * Sum_{n} F(i omega_n))
        into a continuous contour integral format prior to branch cut reduction.
        
        Returns the integrand: f(z) * n_{F/B}(z)
        """
        if statistics not in ['fermion', 'boson']:
            raise ValueError("Statistics must be 'fermion' or 'boson'")
            
        f_z = F_i_omega_n.subs(sp.I * self.omega_n, self.z)
        
        if statistics == 'fermion':
            # Fermi-Dirac distribution n_F(z)
            n_z = 1 / (sp.exp(self.beta * self.z) + 1)
        else:
            # Bose-Einstein distribution n_B(z)
            n_z = 1 / (sp.exp(self.beta * self.z) - 1)
            
        return f_z * n_z

    def analytic_continuation(self, F_z: sp.Expr) -> Tuple[sp.Expr, sp.Expr]:
        """
        Performs analytic continuation mapping z -> omega + i*eta and z -> omega - i*eta,
        which is used to evaluate the discontinuity across the real axis in Retarded/Advanced Green's functions.
        
        Returns:
            Tuple[retarded, advanced]
        """
        retarded = F_z.subs(self.z, self.omega + sp.I * self.eta)
        advanced = F_z.subs(self.z, self.omega - sp.I * self.eta)
        return retarded, advanced

def get_matsubara_engine() -> MatsubaraEngine:
    return MatsubaraEngine()
