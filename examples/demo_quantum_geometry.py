import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

from utils.haldane_model import get_haldane_d_vector
from utils.quantum_geometry_engine import get_quantum_geometry_engine
from utils.plot_engine import get_plot_engine

def generate_haldane_metric_plot():
    print("="*60)
    print(" Quantum Metric Heatmaps for the Haldane Model")
    print("="*60)

    engine = get_quantum_geometry_engine()
    plotter = get_plot_engine()
    kx, ky = engine.kx, engine.ky
    
    # Haldane parameters: t1=1.0, t2=0.1, phi=pi/2, M=0
    # This is a topologically non-trivial gapless/gapped depending on M and t2.
    # With M=0 and phi=pi/2, it is a Chern insulator with C=1 or -1.
    t1_val = 1.0
    t2_val = 0.1
    phi_val = sp.pi / 2
    M_val = 0.0
    
    print("1. Constructing symbolic d-vector for the Haldane model...")
    d_x, d_y, d_z = get_haldane_d_vector(kx, ky, t1_val, t2_val, phi_val, M_val)
    
    print("2. Deriving symbolic Quantum Metric tensor g_uv...")
    metrics = engine.quantum_metric_2band(d_x, d_y, d_z, (kx, ky))
    
    print("3. Compiling to fast numerical functions...")
    # lambdify
    calc_g_xx = sp.lambdify((kx, ky), metrics['xx'], modules='numpy')
    calc_g_yy = sp.lambdify((kx, ky), metrics['yy'], modules='numpy')
    calc_g_xy = sp.lambdify((kx, ky), metrics['xy'], modules='numpy')
    
    print("4. Evaluating on BZ mesh (200x200)...")
    k_range = np.linspace(-np.pi, np.pi, 200, dtype=float)
    Kx, Ky = np.meshgrid(k_range, k_range)
    
    # compute Z arrays
    Z_xx = calc_g_xx(Kx, Ky)
    Z_yy = calc_g_yy(Kx, Ky)
    Z_xy = calc_g_xy(Kx, Ky)
    
    print("5. Rendering APS-standard plots...")
    out_dir = os.path.dirname(__file__)
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_xx, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Quantum Metric $g_{xx}(\mathbf{k})$ of Haldane Model",
        output_path=os.path.join(out_dir, "haldane_g_xx.png"),
        cmap="viridis", zlabel=r"$g_{xx}$"
    )
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_yy, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Quantum Metric $g_{yy}(\mathbf{k})$ of Haldane Model",
        output_path=os.path.join(out_dir, "haldane_g_yy.png"),
        cmap="viridis", zlabel=r"$g_{yy}$"
    )
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_xy, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Quantum Metric $g_{xy}(\mathbf{k})$ of Haldane Model",
        output_path=os.path.join(out_dir, "haldane_g_xy.png"),
        cmap="coolwarm", zlabel=r"$g_{xy}$"
    )

    print("6. Deriving symbolic Christoffel Symbols Γ^l_mn...")
    gamma = engine.christoffel_symbols(metrics, (kx, ky))
    
    print("7. Evaluating Γ^x_xx and Γ^y_yy on BZ mesh...")
    calc_gamma_x_xx = sp.lambdify((kx, ky), gamma['x_xx'], modules='numpy')
    calc_gamma_y_yy = sp.lambdify((kx, ky), gamma['y_yy'], modules='numpy')
    
    # Adding small numerical offset to avoid dividing by absolute zero if it happens at High symmetry points.
    # We will use Kx, Ky directly. If division by zero happens, we handle nan.
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    Z_gamma_x_xx = np.nan_to_num(calc_gamma_x_xx(Kx, Ky), posinf=0, neginf=0)
    Z_gamma_y_yy = np.nan_to_num(calc_gamma_y_yy(Kx, Ky), posinf=0, neginf=0)
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_gamma_x_xx, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Christoffel Symbol $\Gamma^x_{xx}(\mathbf{k})$",
        output_path=os.path.join(out_dir, "haldane_gamma_x_xx.png"),
        cmap="seismic", zlabel=r"$\Gamma^x_{xx}$"
    )
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_gamma_y_yy, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Christoffel Symbol $\Gamma^y_{yy}(\mathbf{k})$",
        output_path=os.path.join(out_dir, "haldane_gamma_y_yy.png"),
        cmap="seismic", zlabel=r"$\Gamma^y_{yy}$"
    )

    print("[SUCCESS] All quantum geometry plot derivations saved successfully.")

from utils.nonlinear_optics_engine import get_nonlinear_optics_engine

def generate_shift_current_plot():
    print("="*60)
    print(" Nonlinear Optics: Shift Current Integrand for Haldane Model")
    print("="*60)
    
    engine = get_quantum_geometry_engine()
    nl_engine = get_nonlinear_optics_engine(engine)
    plotter = get_plot_engine()
    kx, ky = engine.kx, engine.ky
    
    t1_val, t2_val, phi_val = 1.0, 0.1, sp.pi / 2
    
    # 1. Symmetric Case (M = 0)
    print("Calculating Shift Current Integrand for Symmetric Case (M=0)...")
    d_x_sym, d_y_sym, d_z_sym = get_haldane_d_vector(kx, ky, t1_val, t2_val, phi_val, 0.0)
    sig_xxx_sym = nl_engine.shift_current_conductivity_integrand(d_x_sym, d_y_sym, d_z_sym, (kx, ky))['xxx']
    calc_sig_sym = sp.lambdify((kx, ky), sig_xxx_sym, modules='numpy')
    
    # 2. Broken Symmetry Case (M = 0.5)
    print("Calculating Shift Current Integrand for Asymmetric Case (M=0.5)...")
    d_x_asym, d_y_asym, d_z_asym = get_haldane_d_vector(kx, ky, t1_val, t2_val, phi_val, 0.5)
    sig_xxx_asym = nl_engine.shift_current_conductivity_integrand(d_x_asym, d_y_asym, d_z_asym, (kx, ky))['xxx']
    calc_sig_asym = sp.lambdify((kx, ky), sig_xxx_asym, modules='numpy')
    
    k_range = np.linspace(-np.pi, np.pi, 200, dtype=float)
    Kx, Ky = np.meshgrid(k_range, k_range)
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    Z_sym = np.nan_to_num(calc_sig_sym(Kx, Ky), posinf=0, neginf=0)
    Z_asym = np.nan_to_num(calc_sig_asym(Kx, Ky), posinf=0, neginf=0)
    
    out_dir = os.path.dirname(__file__)
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_sym, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Shift Current Integrand $\sigma^{(2)}_{xxx}(\mathbf{k})$ ($M=0$)",
        output_path=os.path.join(out_dir, "haldane_shift_current_M_0.png"),
        cmap="PiYG", zlabel=r"$\sigma^{(2)}_{xxx}$"
    )
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z_asym, 
        xlabel=r"$k_x$", ylabel=r"$k_y$",
        title=r"Shift Current Integrand $\sigma^{(2)}_{xxx}(\mathbf{k})$ ($M=0.5$)",
        output_path=os.path.join(out_dir, "haldane_shift_current_M_0_5.png"),
        cmap="PiYG", zlabel=r"$\sigma^{(2)}_{xxx}$"
    )
    print("[SUCCESS] Shift current plots generated successfully.")

if __name__ == "__main__":
    generate_haldane_metric_plot()
    generate_shift_current_plot()
