import sympy as sp
from typing import Tuple, Dict

class QuantumGeometryEngine:
    """
    Quantum Geometry Engine
    Computes Quantum Metric, Berry Curvature, Christoffel Symbols, and Riemann Curvature Tensor
    for quantum many-body/band models.
    """
    def __init__(self):
        self.kx = sp.Symbol('kx', real=True)
        self.ky = sp.Symbol('ky', real=True)

    def quantum_metric_2band(self, dx: sp.Expr, dy: sp.Expr, dz: sp.Expr, vars_k: Tuple[sp.Symbol, sp.Symbol]) -> Dict[str, sp.Expr]:
        """
        Computes the exact quantum metric g_uv for a 2-band model H = d(k) · σ.
        For the lowest band, g_uv = 1/(4d^2) * (∂_u d · ∂_v d - (d · ∂_u d)(d · ∂_v d) / d^2)
        """
        k1, k2 = vars_k
        d2 = dx**2 + dy**2 + dz**2
        
        # Partial derivatives w.r.t k1 and k2
        dx_1, dy_1, dz_1 = sp.diff(dx, k1), sp.diff(dy, k1), sp.diff(dz, k1)
        dx_2, dy_2, dz_2 = sp.diff(dx, k2), sp.diff(dy, k2), sp.diff(dz, k2)
        
        def g_comp(d_u, d_v):
            dot_uv = d_u[0]*d_v[0] + d_u[1]*d_v[1] + d_u[2]*d_v[2]
            dot_d_u = dx*d_u[0] + dy*d_u[1] + dz*d_u[2]
            dot_d_v = dx*d_v[0] + dy*d_v[1] + dz*d_v[2]
            
            # Combine the formula
            val = (dot_uv - (dot_d_u * dot_d_v) / d2) / (4 * d2)
            # We don't fully simplify here for speed; caller can simplify if needed
            return val
            
        d_1 = (dx_1, dy_1, dz_1)
        d_2 = (dx_2, dy_2, dz_2)
        
        g_xx = g_comp(d_1, d_1)
        g_yy = g_comp(d_2, d_2)
        g_xy = g_comp(d_1, d_2)
        
        return {'xx': g_xx, 'yy': g_yy, 'xy': g_xy, 'yx': g_xy}

    def berry_curvature_2band(self, dx: sp.Expr, dy: sp.Expr, dz: sp.Expr, vars_k: Tuple[sp.Symbol, sp.Symbol]) -> sp.Expr:
        """
        Computes the Berry curvature Ω_xy for a 2-band model H = d(k) · σ.
        Ω_xy = 1/(2d^3) * d · (∂_x d × ∂_y d)  (for the lower band)
        Note: The sign convention might be negative depending on definition, we use 1/(2d^3).
        """
        k1, k2 = vars_k
        d2 = dx**2 + dy**2 + dz**2
        d_norm3 = d2**(sp.S(3)/2)
        
        dx_1, dy_1, dz_1 = sp.diff(dx, k1), sp.diff(dy, k1), sp.diff(dz, k1)
        dx_2, dy_2, dz_2 = sp.diff(dx, k2), sp.diff(dy, k2), sp.diff(dz, k2)
        
        # d · (d_1 × d_2) = dx*(dy_1*dz_2 - dz_1*dy_2) - dy*(dx_1*dz_2 - dz_1*dx_2) + dz*(dx_1*dy_2 - dy_1*dx_2)
        triple_product = dx * (dy_1 * dz_2 - dz_1 * dy_2) \
                         - dy * (dx_1 * dz_2 - dz_1 * dx_2) \
                         + dz * (dx_1 * dy_2 - dy_1 * dx_2)
                         
        omega = triple_product / (2 * d_norm3)
        return omega

    def christoffel_symbols(self, g_metric: Dict[str, sp.Expr], vars_k: Tuple[sp.Symbol, sp.Symbol]) -> Dict[str, sp.Expr]:
        """
        Computes the analytical Christoffel symbols of the second kind Γ^λ_μν.
        g_metric: dict with keys 'xx', 'yy', 'xy' representing the quantum metric
        vars_k: Tuple (kx, ky)
        Returns a dictionary with keys 'x_xx', 'x_xy', 'x_yy', 'y_xx', 'y_xy', 'y_yy'.
        """
        k1, k2 = vars_k
        g_xx = g_metric['xx']
        g_yy = g_metric['yy']
        g_xy = g_metric['xy']
        
        # 1. Compute inverse metric g^uv
        det_g = g_xx * g_yy - g_xy**2
        inv_g_xx = g_yy / det_g
        inv_g_yy = g_xx / det_g
        inv_g_xy = -g_xy / det_g
        
        g_mat = {(1, 1): g_xx, (2, 2): g_yy, (1, 2): g_xy, (2, 1): g_xy}
        inv_g = {(1, 1): inv_g_xx, (2, 2): inv_g_yy, (1, 2): inv_g_xy, (2, 1): inv_g_xy}
        coords = {1: k1, 2: k2}
        
        # 2. Compute partial derivatives of metric partial_a (g_bc)
        dg = {}
        for a in (1, 2):
            for b in (1, 2):
                for c in (1, 2):
                    if b <= c:
                        dg[(a, b, c)] = sp.diff(g_mat[(b, c)], coords[a])
                        dg[(a, c, b)] = dg[(a, b, c)]
                        
        # 3. Compute Christoffel symbols
        Gamma = {}
        for l in (1, 2):
            for m in (1, 2):
                for n in (1, 2):
                    if m <= n:
                        val = sp.S.Zero
                        for s in (1, 2):
                            # Gamma_s,mn = 0.5 * (dg_m(g_ns) + dg_n(g_ms) - dg_s(g_mn))
                            gamma_first = sp.S(1)/2 * (dg[(m, n, s)] + dg[(n, m, s)] - dg[(s, m, n)])
                            val += inv_g[(l, s)] * gamma_first
                        # Simplify could hang on very complex metric, but necessary for analytical checks
                        # We will try to simplify, but it might take some time depending on H
                        Gamma[(l, m, n)] = val
                        Gamma[(l, n, m)] = val
                        
        idx_map = {1: 'x', 2: 'y'}
        res = {}
        for l in (1, 2):
            for m in (1, 2):
                for n in (1, 2):
                    if m <= n:
                        key = f"{idx_map[l]}_{idx_map[m]}{idx_map[n]}"
                        res[key] = sp.cancel(Gamma[(l, m, n)])
        return res

def get_quantum_geometry_engine() -> QuantumGeometryEngine:
    return QuantumGeometryEngine()
