import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sympy as sp
from utils.quantum_geometry_engine import get_quantum_geometry_engine
from utils.haldane_model import get_haldane_d_vector

def test_massive_dirac_metric():
    engine = get_quantum_geometry_engine()
    kx = engine.kx
    ky = engine.ky
    m = sp.Symbol('m', real=True, positive=True)
    
    # Massive Dirac d-vector
    dx = kx
    dy = ky
    dz = m
    
    metrics = engine.quantum_metric_2band(dx, dy, dz, (kx, ky))
    g_xx = sp.simplify(metrics['xx'])
    g_yy = sp.simplify(metrics['yy'])
    g_xy = sp.simplify(metrics['xy'])
    
    # For massive Dirac, setting ky=0, we expect g_xx at kx=0,ky=0 to be 1/(4m^2)
    val_xx = sp.simplify(g_xx.subs({kx: 0, ky: 0}))
    expected_xx = 1 / (4 * m**2)
    assert sp.simplify(val_xx - expected_xx) == 0, f"Expected {expected_xx}, got {val_xx}"
    
    # Berry curvature analysis
    omega = sp.simplify(engine.berry_curvature_2band(dx, dy, dz, (kx, ky)))
    val_omega = sp.simplify(omega.subs({kx: 0, ky: 0}))
    expected_omega = 1 / (2 * m**2)
    assert sp.simplify(val_omega - expected_omega) == 0, f"Expected {expected_omega}, got {val_omega}"
    print("[SUCCESS] Massive Dirac 2-band Quantum Metric & Curvature tests passed.")

def test_christoffel_symbols():
    engine = get_quantum_geometry_engine()
    kx = engine.kx
    ky = engine.ky
    m = sp.Symbol('m', real=True, positive=True)
    
    dx, dy, dz = kx, ky, m
    metrics = engine.quantum_metric_2band(dx, dy, dz, (kx, ky))
    gamma = engine.christoffel_symbols(metrics, (kx, ky))
    
    # We test non-singularity and evaluation at a specific point
    # kx = 1, ky = 0, m = 1
    val = gamma['x_xx'].subs({kx: 1, ky: 0, m: 1})
    assert val.is_real, "Christoffel symbol evaluated to an invalid value."
    print("[SUCCESS] Christoffel symbols symbolically derived and evaluated.")

if __name__ == '__main__':
    test_massive_dirac_metric()
    test_christoffel_symbols()

