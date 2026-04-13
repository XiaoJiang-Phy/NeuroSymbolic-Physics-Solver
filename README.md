# NeuroSymbolic-Physics-Solver

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Status-Experimental%20Prototype-orange.svg" alt="Experimental Prototype">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License MIT">
</p>

A multi-agent, stateful tree-based orchestration system designed to solve complex physics and mathematics problems (integrals, ODEs, etc.) using a combination of **Deep-Reasoning Symbolic Symbolic Intelligence** and **High-Precision Numerical Verification**.

## Recent Solution Success

The solver recently achieved two major zero-error closed-form derivations:

### 1. 1D Tight-Binding Density of States (DOS)
Derived the exact analytic DOS for a 1D nearest-neighbor tight-binding model:
$$D(\omega) = \frac{1}{\pi\sqrt{4t^2 - \omega^2}}, \quad |\omega| < 2t$$

**Key Breakthroughs in CMP Mode:**
- **CMP-Aware Oracle Bypass**: Successfully recognized symbolic CMP constructs (DiracDelta, Heaviside, Non-commuting operators) and used confidence-based heuristics to bypass numerical Oracle crashes during intermediate symbolic transformations.
- **Physical Reasoning**: Navigated from a real-space Hamiltonian to momentum-space, applied Fourier transforms, constructed the Retarded Green's function, and derived the spectral function.
- **Delta Function Integration**: Automatically handled the limit $\eta \to 0^+$ and applied Dirac Delta properties to solve the Brillouin zone integral analytically.
- **Automated Reporting**: Generated a complete academic report: [`report_1D_Tight-Binding_DOS_Derivation.md`](./report_1D_Tight-Binding_DOS_Derivation.md).

### 2. Parametric Sinusoidal Decay Integral
$$I(a) = \int_{0}^{\infty} \frac{\sin(ax)}{x(x^2+1)} \, dx = \frac{\pi}{2}(1 - e^{-a}), \quad a > 0$$

**Key Breakthroughs in this Solution:**
- **Symbolic-Numerical Hybrid**: Swapped integration order via Fubini's theorem and evaluated using standard Fourier cosine transforms.
- **Precision Validation**: Verified against `mpmath` ground-truth at $a \in \{1, 2, 5\}$ with absolute residuals $< 10^{-15}$.
- **Automated Reporting**: Generated a complete academic report: [`report_Parametric_Sinusoidal_Decay_Integral.md`](./report_Parametric_Sinusoidal_Decay_Integral.md).

## Core Architecture

The system utilizes four specialized agents powered by **DeepSeek-R1 (Reasoning)** and **DeepSeek-V3** to iteratively explore the solution space:

1.  **Agent A: The Theorist (DeepSeek-R1)**
    *   **Mechanism**: Performs "Chain-of-Thought" reasoning to propose **Atomic Derivation Steps**.
    *   **Exploration**: Generates 3 differentiated mathematical paths (e.g., Substitution, Integration by Parts, Contour Integration).
    *   **Physics Priors**: Prioritizes paths involving Asymptotic Matching, Singularity Analysis, and Standard Transform recognition.

2.  **Agent B: The Coder (DeepSeek-V3)**
    *   **Translation**: Converts symbolic strategies into executable Python code using `SymPy` and `mpmath`.
    *   **Guardrails**: Implements **Early Exit** point-sampling to prune branches where the symbolic expression deviates from the numerical truth by $>10\%$.

3.  **Agent C: The Verifier (DeepSeek-V3)**
    *   **Logic**: Performs numerical equivalence checks across entire parameter ranges.
    *   **Calculus-Aware**: Interrogates differentiation/integration steps by comparing values to numerical derivatives.
    *   **Categorization**: Prunes the tree and provides feedback to the Theorist if a branch fails.

4.  **Agent D: The Reporter (DeepSeek-V3)**
    *   **Synthesis**: Compiles final research papers or reports in Markdown/LaTeX.
    *   **Post-Mortem**: Analyzes failure logs to document "Dead Ends" and "Turning Points" in the derivation.

## Advanced Features

-   **Best-First Search (BFS)**: Uses a priority queue to explore the most promising mathematical paths first, balancing `success_probability` and `graph_depth`.
-   **Numerical Oracle**: A 50-100 dps engine capable of handling nested integrals, recursive function calls, and symbolic parameter substitutions.
-   **State Management**: Persistent `tree_log.json` allows the solver to resume from the last successful checkpoint after crashes or API timeouts.
-   **Diagnostic Transparency**: All internal "Inner Monologues" (reasoning tokens) from the R1 models are preserved in `thinking_process.txt`.

## Getting Started

### Prerequisites
- Python 3.10+
- Dependencies: `mpmath`, `sympy`, `openai`, `matplotlib`, `python-dotenv`

### Installation
1. Clone the repository.
2. Create a `.env` file:
   ```env
   DEEPSEEK_API_KEY=your_key_here
   ```

### Execution
```bash
python orchestrator.py
```

## 📂 Project Structure
- `orchestrator.py`: Root loop and search manager.
- `agents/`: Core AI instructions and solver logic.
- `utils/numerical_oracle.py`: High-precision calculus engine.
- `tree_log.json`: The "Long-term Memory" of the solution tree.
- `thinking_process.txt`: Integrated reasoning and execution logs.
- `report_*.md`: Final scientific outputs.

## License
MIT
