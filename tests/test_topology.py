import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sympy as sp
from sympy.physics.matrices import msigma
from utils.topology_engine import get_topology_engine
from utils.topology_engine import get_topology_engine

def test_topology_engine():
    topo = get_topology_engine()
    
    # Let's test with a simple 2-band Weyl-like / Dirac-like Hamiltonian:
    # H = kx * sigma_x + ky * sigma_y + m * sigma_z
    kx = topo.kx
    ky = topo.ky
    m = sp.Symbol('m', real=True, positive=True) # positive mass
    
    H = kx * msigma(1) + ky * msigma(2) + m * msigma(3)
    
    # We expect the Berry curvature of the lower band (band_index=0) to be tightly peaked around k=0.
    # The analytical result for such a 2-band model is Omega_-(k) = m / (2 * (k^2 + m^2)^(3/2))
    # where k^2 = kx^2 + ky^2
    
    berry_curv = topo.berry_curvature_from_hamiltonian(H, (kx, ky), band_index=0)
    
    val = sp.simplify(berry_curv.subs({kx: 1, ky: 0, m: 1}))
    expected_val = 1 / (4 * sp.sqrt(2))
    
    # We use float to avoid tiny symbolic residuals
    assert abs(float(val) - float(expected_val)) < 1e-7, f"Expected {expected_val}, got {val}"
    
    print("Topology Engine Output at (kx=1, ky=0, m=1):", val)
    print("Topology Engine Tests Passed!")

if __name__ == '__main__':
    test_topology_engine()
