"""
╔══════════════════════════════════════════════════════════════════╗
║  Altermagnetic AHC — Physical Analysis & Symmetry Breaking       ║
║                                                                  ║
║  KEY FINDING: σ_xy ≡ 0 for the pure d-wave altermagnet+Rashba    ║
║  This is EXACT due to C_{4z} symmetry of the Hamiltonian:        ║
║                                                                  ║
║    Under C4: (kx,ky) → (ky,-kx)                                 ║
║    Berry curvature: Ω_z → -Ω_z  (d-wave, cos2θ→-cos2θ)         ║
║    Energy: E_-(k,θ) → E_-(k,θ+π/2) but cos²(2θ) is invariant   ║
║    So the Fermi surface IS 4-fold symmetric!                     ║
║    Therefore: ∫ Ω_z f(E_-) dθ = 0 for ANY μ.                    ║
║                                                                  ║
║  To get nonzero AHE, we must BREAK C4 symmetry.                 ║
║  Physical mechanisms:                                            ║
║    1. Uniaxial strain → J_x ≠ J_y                               ║
║    2. Zeeman field along z → shifts E_± differently              ║
║    3. Warping term ~ k⁴cos(4θ)                                  ║
║                                                                  ║
║  We implement Option 1: anisotropic exchange                     ║
║    H_AM → J_x kx² σ_z - J_y ky² σ_z  (J_x ≠ J_y)              ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from scipy import integrate
from utils.plot_engine import get_plot_engine
from utils.physics_auditor import get_physics_auditor

SECTION = lambda n, title: print(f"\n{'━'*64}\n  STEP {n}: {title}\n{'━'*64}")
PASS    = lambda msg: print(f"    ✅ {msg}")
FAIL    = lambda msg: print(f"    ❌ {msg}")
NOTE    = lambda msg: print(f"    📝 {msg}")

# ══════════════════════════════════════════════════════════════════
# Parameters
# ══════════════════════════════════════════════════════════════════
alpha = 0.5
m_eff = 1.0

def compute_sigma_xy(Jx, Jy, mu_values, k_max=6.0, n_k=600, n_theta=400):
    """
    Compute σ_xy(μ) for anisotropic altermagnet:
      d = (α ky, -α kx, Jx kx² - Jy ky²)
    
    Berry curvature (generalized from Theorist's derivation):
      Numerator: d · (∂_kx d × ∂_ky d)
      = α² (Jy ky² - Jx kx²) + 2αJx·kx·αky·(something)...
      
    Actually, let's just compute it properly for the general case.
    """
    k_grid = np.linspace(0.005, k_max, n_k)
    theta_grid = np.linspace(0, 2*np.pi, n_theta, endpoint=False)
    dk = k_grid[1] - k_grid[0]
    dtheta = theta_grid[1] - theta_grid[0]
    
    K, TH = np.meshgrid(k_grid, theta_grid)
    kx = K * np.cos(TH)
    ky = K * np.sin(TH)
    
    # d-vector components
    dx = alpha * ky
    dy = -alpha * kx
    dz = Jx * kx**2 - Jy * ky**2
    
    # ∂_kx d
    dkx_x = np.zeros_like(kx)
    dkx_y = -alpha * np.ones_like(kx)
    dkx_z = 2 * Jx * kx
    
    # ∂_ky d
    dky_x = alpha * np.ones_like(ky)
    dky_y = np.zeros_like(ky)
    dky_z = -2 * Jy * ky
    
    # Cross product ∂_kx d × ∂_ky d
    cx = dkx_y * dky_z - dkx_z * dky_y
    cy = dkx_z * dky_x - dkx_x * dky_z
    cz = dkx_x * dky_y - dkx_y * dky_x
    
    # Triple product d · (∂_kx d × ∂_ky d)
    triple = dx * cx + dy * cy + dz * cz
    
    # |d|² and |d|³
    d_sq = dx**2 + dy**2 + dz**2
    d_sq = np.maximum(d_sq, 1e-30)  # avoid division by zero
    d_cube = d_sq**1.5
    
    # Berry curvature: Ω_z = - triple / (2 |d|³)
    Omega = -triple / (2.0 * d_cube)
    
    # Energy: E_- = k²/(2m) - |d|
    E_minus = K**2 / (2*m_eff) - np.sqrt(d_sq)
    
    # k · Ω_z for integration measure
    integrand = K * Omega
    
    sigma_xy = np.zeros(len(mu_values))
    for i, mu in enumerate(mu_values):
        occupied = (E_minus <= mu).astype(float)
        sigma_xy[i] = np.sum(integrand * occupied) * dk * dtheta / (2 * np.pi)
    
    return sigma_xy, Omega, E_minus, K, TH


def main():
    print("╔" + "═"*66 + "╗")
    print("║  Altermagnetic AHC — Symmetry Analysis & C4 Breaking           ║")
    print("╚" + "═"*66 + "╝")

    # ================================================================
    # STEP 1: Verify C4-symmetric case gives σ_xy = 0
    # ================================================================
    SECTION(1, "Verify: C4-symmetric (Jx=Jy=1) → σ_xy ≡ 0")
    
    mu_values = np.linspace(-8, 0, 150)
    sigma_sym, _, _, _, _ = compute_sigma_xy(Jx=1.0, Jy=1.0, mu_values=mu_values)
    
    print(f"    max|σ_xy| = {np.max(np.abs(sigma_sym)):.2e} (should be ~0)")
    if np.max(np.abs(sigma_sym)) < 1e-6:
        PASS("Confirmed: σ_xy ≡ 0 for C4-symmetric altermagnet. This is exact.")
        NOTE("Physical reason: C4z maps Ω_z → -Ω_z but preserves E_-(k).")
        NOTE("So ∫ Ω_z · Θ(μ-E_-) d²k = 0 for any μ.")
    else:
        FAIL(f"Unexpected nonzero σ_xy = {np.max(np.abs(sigma_sym)):.6f}")

    # ================================================================
    # STEP 2: Break C4 with uniaxial strain (Jx ≠ Jy)
    # ================================================================
    SECTION(2, "C4-broken: Uniaxial strain (Jx=1.0, Jy=0.6)")
    
    Jx, Jy = 1.0, 0.6
    sigma_broken, Omega_broken, E_broken, K_g, TH_g = compute_sigma_xy(
        Jx=Jx, Jy=Jy, mu_values=mu_values, n_k=800, n_theta=600
    )
    
    print(f"    max|σ_xy| = {np.max(np.abs(sigma_broken)):.6f} e²/h")
    peak_idx = np.argmax(np.abs(sigma_broken))
    print(f"    Peak at μ = {mu_values[peak_idx]:.3f}")
    
    if np.max(np.abs(sigma_broken)) > 1e-4:
        PASS(f"Non-zero AHE detected! Peak σ_xy = {sigma_broken[peak_idx]:.6f} e²/h at μ={mu_values[peak_idx]:.3f}")
    else:
        NOTE("Still very small — trying larger anisotropy")

    # ================================================================
    # STEP 3: Scan different strain levels
    # ================================================================
    SECTION(3, "Strain dependence: σ_xy peak vs Jy/Jx")
    
    Jy_values = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0]
    peak_sigma = []
    sigma_curves = []
    
    for Jy_test in Jy_values:
        s, _, _, _, _ = compute_sigma_xy(Jx=1.0, Jy=Jy_test, mu_values=mu_values, n_k=600, n_theta=400)
        peak_val = s[np.argmax(np.abs(s))]
        peak_sigma.append(peak_val)
        sigma_curves.append(s)
        print(f"    Jy/Jx = {Jy_test:.2f}  →  peak σ_xy = {peak_val:+.6f} e²/h")
    
    # ================================================================
    # STEP 4: Physics Audit
    # ================================================================
    SECTION(4, "Physics Audit")
    
    auditor = get_physics_auditor()
    
    NOTE("Key finding: σ_xy ≡ 0 for isotropic d-wave altermagnet (Jx=Jy)")
    NOTE("This is protected by C_{4z} symmetry of the Hamiltonian.")
    NOTE("Breaking C4 via uniaxial strain (Jx≠Jy) yields nonzero AHE.")
    
    auditor.log_decision(
        context="Altermagnetic AHC - Symmetry analysis",
        hypothesis="σ_xy=0 is protected by C4z symmetry; strain breaks it",
        failure_mode="Initial expectation of non-zero AHE in C4-symmetric case was wrong",
        causality="C4z: Ω_z(C4 k) = -Ω_z(k) but E_-(C4 k) = E_-(k) ⟹ exact cancellation",
        pivot="Introduced anisotropic exchange (Jx≠Jy) to access non-trivial AHE"
    )
    PASS("Decision logged")

    # ================================================================
    # STEP 5: Publication Plots
    # ================================================================
    SECTION(5, "Publication-Quality Plots")
    
    plotter = get_plot_engine()
    plot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")

    # ── Plot 1: σ_xy(μ) for different strains ──
    try:
        labels = [rf"$J_y/J_x={Jy:.1f}$" for Jy in Jy_values]
        plot_path = os.path.join(plot_dir, "altermagnet_sigma_xy_strain.png")
        plotter.plot_1d_curves(
            x=mu_values,
            y_list=sigma_curves,
            labels=labels,
            xlabel=r"Chemical Potential $\mu$ (a.u.)",
            ylabel=r"$\sigma_{xy}$ ($e^2/h$)",
            title=r"Altermagnetic AHE: Strain Dependence",
            output_path=plot_path
        )
        PASS(f"Strain-dependent σ_xy(μ) → {plot_path}")
    except Exception as e:
        FAIL(f"Plot 1 failed: {e}")

    # ── Plot 2: Berry curvature for broken C4 case ──
    try:
        kx_arr = K_g * np.cos(TH_g)
        ky_arr = K_g * np.sin(TH_g)

        # Regrid to Cartesian for heatmap
        k_hm = np.linspace(-3, 3, 500)
        Kx_c, Ky_c = np.meshgrid(k_hm, k_hm)
        
        dx_c = alpha * Ky_c
        dy_c = -alpha * Kx_c
        dz_c = Jx * Kx_c**2 - Jy * Ky_c**2
        triple_c = (dx_c * ((-alpha)*(-2*Jy*Ky_c) - (2*Jx*Kx_c)*0) +
                     dy_c * ((2*Jx*Kx_c)*alpha - 0*(-2*Jy*Ky_c)) +
                     dz_c * (0*0 - (-alpha)*alpha))
        d_sq_c = dx_c**2 + dy_c**2 + dz_c**2
        d_sq_c = np.maximum(d_sq_c, 1e-30)
        Omega_c = -triple_c / (2.0 * d_sq_c**1.5)
        vmax = np.percentile(np.abs(Omega_c[Omega_c != 0]), 99)
        Omega_c = np.clip(Omega_c, -vmax, vmax)

        plot_path_2 = os.path.join(plot_dir, "altermagnet_berry_C4broken.png")
        plotter.plot_2d_heatmap(
            Kx_c, Ky_c, Omega_c,
            xlabel=r"$k_x$ (a.u.)", ylabel=r"$k_y$ (a.u.)",
            title=rf"Berry Curvature ($J_x={Jx}, J_y={Jy}$, C4 broken)",
            output_path=plot_path_2,
            cmap="RdBu_r",
            zlabel=r"$\Omega_z$ (a.u.)"
        )
        PASS(f"Broken-C4 Berry curvature → {plot_path_2}")
    except Exception as e:
        FAIL(f"Plot 2 failed: {e}")

    # ════════════════════════════════════════════════════
    print("\n" + "═"*66)
    print("  Analysis complete! ✅")
    print("═"*66)


if __name__ == "__main__":
    main()
