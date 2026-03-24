"""
╔══════════════════════════════════════════════════════════════════╗
║  NeuroSymbolic Physics Solver — Scientific Plotting Demo         ║
║                                                                  ║
║  This example generates a publication-quality heatmap of the    ║
║  Berry Curvature for a Massive Dirac Cone, demonstrating the     ║
║  integration of the TopologyEngine and PlotEngine.               ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp
import numpy as np
from sympy.physics.matrices import msigma

from utils.topology_engine import get_topology_engine
from utils.plot_engine import get_plot_engine

def generate_berry_curvature_plot():
    print("="*60)
    print(" Generating Berry Curvature Plot for Massive Dirac Cone")
    print("="*60)

    # 1. Symbolic Derivation Setup
    topo = get_topology_engine()
    plotter = get_plot_engine()
    
    kx, ky = topo.kx, topo.ky
    m_sym = sp.Symbol('m', real=True, positive=True)
    
    # H = kx * sigma_x + ky * sigma_y + m * sigma_z
    H = kx * msigma(1) + ky * msigma(2) + m_sym * msigma(3)
    
    print("1. Calculating analytical Berry Curvature Omega(k) via Kubo formula...")
    berry_curv_expr = topo.berry_curvature_from_hamiltonian(H, (kx, ky), band_index=0)
    
    # We substitute a specific mass to make it numerical
    m_val = 0.5
    berry_curv_eval = berry_curv_expr.subs(m_sym, m_val)
    print(f"2. Fixing mass gap m = {m_val} eV.")
    
    # Using sympy's lambdify to create a fast NumPy-compatible numeric function
    print("3. Compiling symbolic expression to C-speed numerical function...")
    # Because there's a complex conjugation in the raw sympy expression, we wrap in sp.re to get real part
    lambdified_omega = sp.lambdify((kx, ky), sp.re(berry_curv_eval), modules='numpy')

    # 4. Generate k-space grid
    print("4. Evaluating on 200x200 k-space meshgrid...")
    k_range = np.linspace(-3, 3, 200)
    Kx, Ky = np.meshgrid(k_range, k_range)
    
    # Compute generic Z
    # Handle the divide by zero numerically just in case, though lambdify usually handles it
    Z = lambdified_omega(Kx, Ky)
    
    # 5. Plotting via PlotEngine
    plot_path = os.path.join(os.path.dirname(__file__), "berry_curvature_aps.pdf")
    plot_path_png = os.path.join(os.path.dirname(__file__), "berry_curvature_aps.png")
    
    print("5. Rendering APS-standard plots...")
    # We save both PDF (for LaTeX) and PNG (for quick viewing)
    plotter.plot_2d_heatmap(
        Kx, Ky, Z, 
        xlabel=r"$k_x \ (\mathrm{\AA}^{-1})$", 
        ylabel=r"$k_y \ (\mathrm{\AA}^{-1})$",
        title=r"Berry Curvature $\Omega_-(\mathbf{k})$ of Massive Dirac Cone",
        output_path=plot_path,
        cmap="magma",
        zlabel=r"$\Omega_-$ (a.u.)"
    )
    
    plotter.plot_2d_heatmap(
        Kx, Ky, Z, 
        xlabel=r"$k_x \ (\mathrm{\AA}^{-1})$", 
        ylabel=r"$k_y \ (\mathrm{\AA}^{-1})$",
        title=r"Berry Curvature $\Omega_-(\mathbf{k})$ of Massive Dirac Cone",
        output_path=plot_path_png,
        cmap="magma",
        zlabel=r"$\Omega_-$ (a.u.)"
    )
    
    print(f"\n[SUCCESS] Plots saved to {os.path.dirname(__file__)}")
    print(f"   -> {plot_path}")
    print(f"   -> {plot_path_png}")

if __name__ == "__main__":
    generate_berry_curvature_plot()
