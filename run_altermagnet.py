"""
╔══════════════════════════════════════════════════════════════╗
║  REAL Research Run: Altermagnetic Anomalous Hall Effect       ║
║  This is NOT a happy-path demo. The Theorist Agent           ║
║  (DeepSeek-R1) will autonomously reason through this.        ║
╚══════════════════════════════════════════════════════════════╝

Research Question (2026 frontier):
  For a 2D d-wave altermagnet with Rashba spin-orbit coupling,
  derive the anomalous Hall conductivity sigma_xy as a function
  of chemical potential mu.

  Key physics:
  - Altermagnets have ZERO net magnetization but d-wave spin splitting
  - Their Berry curvature has four-fold symmetry (positive+negative lobes)
  - With SOC, the nodes are gapped, creating net Berry flux
  - sigma_xy(mu) should show non-trivial dependence on Fermi level

  This is a genuinely open-ended calculation — the Theorist must
  figure out how to handle the interplay of d-wave exchange + SOC.
"""

import os, sys, json

# Clear old search state so we start fresh
for f in ["tree_log.json", "thinking_process.txt"]:
    if os.path.exists(f):
        os.remove(f)
        print(f"[Setup] Cleared {f}")

from core.orchestrator import ResearchOrchestrator

problem = {
    "name": "Altermagnetic Anomalous Hall Conductivity",
    "hamiltonian": (
        "H(k) = (kx^2 + ky^2)/(2m) * I_2x2 "
        "+ J*(kx^2 - ky^2) * sigma_z "
        "+ alpha*(ky*sigma_x - kx*sigma_y). "
        "This is a 2D d-wave altermagnet with Rashba SOC. "
        "J is the altermagnetic exchange, alpha is Rashba coupling."
    ),
    "target": (
        "Derive the Berry curvature Omega_z(k) of the lower band analytically, "
        "then compute the anomalous Hall conductivity "
        "sigma_xy = (e^2/hbar) * (1/2pi) * integral Omega_z(k) f(E_-(k)) d^2k "
        "as a function of chemical potential mu at T=0. "
        "Show that sigma_xy is zero when the Fermi level is at the band bottom "
        "or far above both bands, but non-zero at intermediate filling."
    ),
    "hint": (
        "1. The Hamiltonian has the form H = epsilon(k)*I + d(k).sigma where "
        "d = (alpha*ky, -alpha*kx, J*(kx^2-ky^2)). "
        "2. Berry curvature for 2-band model: "
        "Omega = (1/2) * d_hat . (partial_kx d_hat x partial_ky d_hat). "
        "3. The d-wave factor (kx^2-ky^2) changes sign under 90-degree rotation, "
        "so Omega has four-fold symmetry with alternating signs. "
        "4. The total Chern number is zero, but sigma_xy(mu) is non-trivial."
    ),
    "parameters": ["J=1.0", "alpha=0.5", "m=1.0"],
    "description": (
        "Altermagnetism is a newly classified magnetic phase (2022-2024) "
        "with zero net magnetization but momentum-dependent spin splitting. "
        "This problem asks for the anomalous Hall conductivity arising from "
        "Berry curvature in the presence of Rashba SOC, which gaps the "
        "altermagnetic nodal lines and creates non-trivial topology."
    ),
}

orchestrator = ResearchOrchestrator(problem, report_language="Chinese")
orchestrator.run()
