import sympy as sp
from sympy.physics.matrices import msigma

def get_haldane_d_vector(kx: sp.Symbol, ky: sp.Symbol, t1: sp.Expr, t2: sp.Expr, phi: sp.Expr, M: sp.Expr):
    """
    Returns the (dx, dy, dz) components of the Haldane model.
    Uses an orthogonal momentum basis mapping for faster symbolic evaluation
    while maintaining the exact topology of the honeycomb lattice.
    """
    d_x = t1 * (1 + sp.cos(kx) + sp.cos(ky))
    d_y = t1 * (sp.sin(kx) + sp.sin(ky))
    d_z = M - 2 * t2 * sp.sin(phi) * (sp.sin(kx) - sp.sin(ky) - sp.sin(kx - ky))
    return d_x, d_y, d_z

def get_haldane_hamiltonian(kx: sp.Symbol, ky: sp.Symbol, t1: sp.Expr, t2: sp.Expr, phi: sp.Expr, M: sp.Expr) -> sp.Matrix:
    """
    Returns the symbolic 2x2 Hamiltonian matrix for the Haldane model.
    H(k) = d_x(k)*sigma_x + d_y(k)*sigma_y + d_z(k)*sigma_z
    """
    d_x, d_y, d_z = get_haldane_d_vector(kx, ky, t1, t2, phi, M)
    
    H = d_x * msigma(1) + d_y * msigma(2) + d_z * msigma(3)
    return H
