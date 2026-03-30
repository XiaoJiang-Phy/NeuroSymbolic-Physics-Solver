import sympy as sp
from typing import Tuple, Dict

class NonlinearOpticsEngine:
    """
    Nonlinear Optics Engine
    Utilizes quantum geometry (Metric g_uv and Christoffel symbols Γ^λ_μν)
    to compute second-order (and higher) optical responses such as Shift Current.
    """
    def __init__(self, geometry_engine=None):
        if geometry_engine is None:
            from utils.quantum_geometry_engine import get_quantum_geometry_engine
            self.geo_engine = get_quantum_geometry_engine()
        else:
            self.geo_engine = geometry_engine
            
        self.kx = self.geo_engine.kx
        self.ky = self.geo_engine.ky

    def shift_vector_from_christoffel(self, christoffel: Dict[str, sp.Expr]) -> Dict[str, sp.Expr]:
        """
        Computes the Shift Vector R_abc using the Bures/Nonadiabatic connection framework.
        In the two-band non-interacting limit, the intrinsic geometric contribution to
        the shift vector R^a_bc is precisely given by the negative Christoffel symbol:
        R^a_{bc} = - Γ^a_{bc}
        
        Args:
            christoffel: Dictionary of Christoffel symbols, e.g. {'x_xx': expr, ...}
            
        Returns:
            Dictionary of Shift vectors R^a_bc.
        """
        shift_vec = {}
        for key, expr in christoffel.items():
            shift_vec[key] = -expr
        return shift_vec

    def shift_current_conductivity_integrand(self, dx: sp.Expr, dy: sp.Expr, dz: sp.Expr, vars_k: Tuple[sp.Symbol, sp.Symbol]) -> Dict[str, sp.Expr]:
        """
        Derives the integrand for the DC Shift Current Conductivity tensor σ^(2)_abc.
        The formula derived from the nonadiabatic connection maps to:
        Integrand^(2)_abc(k) ~ f_bc(k) * R^a_bc(k)
        where f_bc(k) matches the quantum metric component g_bc(k) for a two-band transition,
        resulting in:
        I_abc = g_{bc} * R^a_{bc} = - g_{bc} * Γ^a_{bc}
        
        Returns a dictionary of integrand expressions in k-space.
        """
        k1, k2 = vars_k
        
        # 1. Compute Metric
        metric = self.geo_engine.quantum_metric_2band(dx, dy, dz, vars_k)
        
        # 2. Compute Christoffel
        gamma = self.geo_engine.christoffel_symbols(metric, vars_k)
        
        # 3. Compute Integrands I_abc = - g_bc * Γ^a_bc
        # Indices: a = current direction, b,c = polarization directions
        integrands = {}
        
        # x-polarized light, x-current (sigma_xxx)
        integrands['xxx'] = sp.simplify(-metric['xx'] * gamma['x_xx'])
        
        # y-polarized light, y-current (sigma_yyy)
        integrands['yyy'] = sp.simplify(-metric['yy'] * gamma['y_yy'])
        
        # x-current from y-polarized light (sigma_xyy)
        integrands['xyy'] = sp.simplify(-metric['yy'] * gamma['x_yy'])
        
        # y-current from x-polarized light (sigma_yxx)
        integrands['yxx'] = sp.simplify(-metric['xx'] * gamma['y_xx'])
        
        return integrands

def get_nonlinear_optics_engine() -> NonlinearOpticsEngine:
    return NonlinearOpticsEngine()
