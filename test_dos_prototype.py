import os
import sys
import sympy as sp
from mpmath import mp
from agents.verifier_agent import VerifierAgent

def test_dos_derivation_and_verification():
    print("--- 1D Tight-Binding DOS Derivation & Verification ---")
    
    k, omega = sp.symbols('k omega', real=True)
    t = sp.symbols('t', positive=True) 
    
    # Atomic Steps Representation
    # 1. Real -> k-space
    eps_k = -2 * t * sp.cos(k)
    print(f"1. Dispersion relation: eps(k) = {eps_k}")
    
    # 2. k-space -> frequency space -> Analytical continuation -> Imaginary part (Delta function)
    # Retarded Green's Function G^R(k, omega) = 1 / (omega - eps_k + i*eta)
    # Im[G^R] / (-pi) -> delta(omega - eps_k)
    # Roots of omega - eps_k = 0 are k = +/- acos(omega/(2*t))
    # Derivative is 2*t*sin(k) = 2*t*sqrt(1 - (omega/(2t))^2)
    # Sum over roots gives a factor of 2.
    # Integrating over k in [-pi, pi] gives the DOS:
    
    dos_expr = 1 / (2 * sp.pi * t * sp.sqrt(1 - (omega/(2*t))**2))
    print(f"2. Derived DOS expression: D(omega) = {dos_expr}")
    
    # 3. Verification step using Verifier
    print("\n3. Generating temporary evaluation script for VerifierAgent...")
    script_content = f"""
import sympy as sp
from sympy import pi, sqrt, cos, sin, exp, log
from mpmath import mp

mp.dps = 50
omega, t = sp.symbols('omega t', real=True, positive=True)

# Definition of the derived DOS
dos = {dos_expr}

# Substitute physical parameters (t = 1) for numerical verification
# Also evaluate at t=1 so that the piecewise/integral evaluates computationally
dos_sub = dos.subs(t, 1)
omega_bounds_lower = -2*1
omega_bounds_upper = 2*1

# Integrate over the full bandwidth [-2t, 2t] with t=1
# Since it's symmetric and well-known, we can just do the sp.integrate
# Note: sympy piecewise integration can be slow, let's use mpmath for numerical integration
def integrand(w):
    return float(dos_sub.subs(omega, w).evalf())

try:
    integral_res = mp.quad(integrand, [omega_bounds_lower, omega_bounds_upper])
    print(integral_res)
except Exception as e:
    # If mpmath singularity evaluation fails, try a tiny offset
    integral_res = mp.quad(integrand, [omega_bounds_lower + 1e-10, omega_bounds_upper - 1e-10])
    print(integral_res)
"""
    
    temp_script_path = "temp_dos_eval.py"
    with open(temp_script_path, "w", encoding='utf-8') as f:
        f.write(script_content.strip())
        
    verifier = VerifierAgent()
    print("   Running VerifierAgent with Oracle value = 1.0 ...")
    
    # The sum rule requires the integral of DOS over all energies to equal 1
    result = verifier.verify(temp_script_path, oracle_val=1.0)
    
    if result.get("status") == "SUCCESS":
        print(f"\n[PASS] Node TDD Verification Successful.")
        print(f"Residual: {result.get('residual')}")
        
        # Log to DECISION_LOG.md
        log_entry = (
            "## Node: Prototype Task - 1D DOS Derivation & Verification\n"
            "- **Action**: Implemented the atomic derivation steps for the 1D tight-binding DOS and verified its full-bandwidth integral.\n"
            "- **Mathematical Validation**: The DOS $D(\\omega) = 1 / (2\\pi t \\sqrt{1 - (\\omega/2t)^2})$ integrates perfectly to $1$ over $\\omega \\in [-2t, 2t]$.\n"
            "- **Physics Rationale**: The normalization follows from the spectral weight sum rule, where the integral of the spectral function $A(k,\\omega)$ over all energies is 1, and the momentum integral over the first Brillouin zone preserves this normalization.\n"
            "- **Status**: PASS\n\n"
        )
        
        mode = "a" if os.path.exists("DECISION_LOG.md") else "w"
        with open("DECISION_LOG.md", mode, encoding="utf-8") as f:
            f.write(log_entry)
            
        print("   Decision Footprint captured in DECISION_LOG.md.")
    else:
        print(f"\n[FAIL] Verification Failed: {result}")
        sys.exit(1)
        
    # Cleanup
    if os.path.exists(temp_script_path):
        os.remove(temp_script_path)

if __name__ == "__main__":
    test_dos_derivation_and_verification()
