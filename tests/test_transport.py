import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sympy as sp
from utils.transport_engine import get_transport_engine

def test_transport_engine():
    trans = get_transport_engine()
    
    kx, ky = sp.symbols('kx ky', real=True)
    tau = sp.Symbol('tau', real=True, positive=True)
    m = sp.Symbol('m', real=True, positive=True)
    
    # Simple parabolic band E(k) = hbar^2 k^2 / 2m
    E_k = trans.hbar**2 * (kx**2 + ky**2) / (2 * m)
    
    # 1. Test Drude velocity
    v_x = trans.velocity_operator(E_k, kx)
    assert sp.simplify(v_x - (trans.hbar * kx / m)) == 0, "Velocity operator failed for parabolic band."
    
    # 2. Test Drude conductivity shape
    sigma_xx_integrand = trans.drude_conductivity_integrand(E_k, tau, kx, kx)
    expected_v_term = trans.e**2 * tau * (trans.hbar * kx / m)**2 * sp.DiracDelta(E_k - trans.mu)
    assert sp.simplify(sigma_xx_integrand - expected_v_term) == 0, "Drude integrand mismatched."
    
    # 3. Test Anomalous Hall connection
    Omega = sp.Symbol('Omega', real=True)
    sigma_xy = trans.anomalous_hall_conductivity_integrand(Omega, E_k)
    # Check if Heaviside distribution is embedded
    assert sigma_xy.has(sp.Heaviside), "Anomalous Hall lacks T=0 Fermi distribution (Heaviside/Step)."
    assert sigma_xy.has(trans.e**2 / trans.hbar), "Anomalous Hall prefactor mismatched."
    
    print("Transport Engine Tests Passed!")

if __name__ == '__main__':
    test_transport_engine()
