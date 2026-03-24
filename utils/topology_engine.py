import sympy as sp
from typing import List, Tuple

class TopologyEngine:
    """
    Phase 4.1: Topology & Invariants Engine
    Provides symbolic utilities to compute Berry Connections, Berry Curvature,
    and Chern Numbers starting from a k-space Hamiltonian matrix H(k).
    """
    def __init__(self):
        # Default 2D momentum parameters for topology
        self.kx = sp.Symbol('kx', real=True)
        self.ky = sp.Symbol('ky', real=True)
        self.kz = sp.Symbol('kz', real=True)

    def berry_curvature_from_hamiltonian(self, H: sp.Matrix, vars_k: Tuple[sp.Symbol, sp.Symbol], band_index: int = 0) -> sp.Expr:
        """
        Computes the Berry Curvature Omega_n(k) for a specific band n
        using the gauge-independent Kubo-like formula:
        Omega_n = -2 * Im [ sum_{m != n} <n| d_{kx}H |m><m| d_{ky}H |n> / (En - Em)^2 ]
        
        Args:
            H: The Hamiltonian matrix (e.g. 2x2 for a two-band model).
            vars_k: Tuple of two momentum symbols, e.g., (kx, ky).
            band_index: The index of the band (sorted by energy). Default is 0 (lowest band).
            
        Returns:
            A SymPy expression for the Berry curvature Omega.
        """
        kx, ky = vars_k
        
        # 1. Diagonalize H to get eigenvalues and eigenvectors.
        # H.eigenvects() returns a list of tuples: (eigenval, multiplicity, [eigenvectors])
        # We sort them by eigenvalue (using a heuristic for sorting symbolic expressions, or just assume they are sorted if simple)
        # Note: SymPy's sorting of symbolic expressions can be tricky, so we trust the order or ask the user to simplify.
        eigen_data = H.eigenvects()
        
        # Flatten and normalize vectors
        bands = []
        for val, mult, vecs in eigen_data:
            for v in vecs:
                norm = sp.sqrt(sp.simplify((v.H * v)[0, 0]))
                normalized_v = v / norm
                bands.append((val, normalized_v))
                
        # Sort by eigenvalue algebraically if possible, though exact sorting might fail. 
        # We'll just leave them in the order SymPy returns unless they are numeric.
        try:
            bands.sort(key=lambda x: x[0])
        except TypeError:
            pass # Cannot sort symbolic expressions directly safely
            
        if len(bands) <= 1:
            return sp.S.Zero
            
        if band_index >= len(bands):
            raise ValueError(f"Requested band index {band_index} out of bounds for {len(bands)}-band Hamiltonian.")
            
        En, state_n = bands[band_index]
        dH_dkx = sp.diff(H, kx)
        dH_dky = sp.diff(H, ky)
        
        Omega_n = sp.S.Zero
        for m, (Em, state_m) in enumerate(bands):
            if m == band_index:
                continue
            
            # Matrix elements: <n| dH/dkx |m> and <m| dH/dky |n>
            mat_el_x = (state_n.H * dH_dkx * state_m)[0, 0]
            mat_el_y = (state_m.H * dH_dky * state_n)[0, 0]
            
            # Numerator: <n| dH/dkx |m><m| dH/dky |n> - (x <-> y)
            mat_el_y_rev = (state_n.H * dH_dky * state_m)[0, 0]
            mat_el_x_rev = (state_m.H * dH_dkx * state_n)[0, 0]
            
            num = mat_el_x * mat_el_y - mat_el_y_rev * mat_el_x_rev
            
            # Omega_n = i * sum [...] (which is equivalent to -2 Im [...])
            term = sp.I * num / (En - Em)**2
            Omega_n += term
            
        return sp.simplify(Omega_n)

    def chern_number(self, berry_curvature: sp.Expr, vars_k: Tuple[sp.Symbol, sp.Symbol], bounds: Tuple[Tuple[sp.Expr, sp.Expr], Tuple[sp.Expr, sp.Expr]]) -> sp.Integral:
        """
        Sets up the integration for the Chern number:
        C = 1 / (2*pi) \int \int dkx dky \Omega(kx, ky)
        
        Returns a SymPy formal Integral.
        """
        kx, ky = vars_k
        bound_x, bound_y = bounds
        
        integral = sp.Integral(berry_curvature, (kx, bound_x[0], bound_x[1]), (ky, bound_y[0], bound_y[1]))
        return (1 / (2 * sp.pi)) * integral


def get_topology_engine() -> TopologyEngine:
    return TopologyEngine()
