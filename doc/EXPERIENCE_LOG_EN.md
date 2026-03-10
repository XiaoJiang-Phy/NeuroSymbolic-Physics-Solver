# Project Experience Log: NeuroSymbolic Physics Solver

## 1. Technical "Trenches": The Reality of Long-Reasoning Models

Developing with **DeepSeek-R1** (a long-reasoning model) presented unique challenges that standard LLM pipelines do not encounter.

### The Network Instability & KeyboardInterrupt
- **Problem**: R1 often spends 60-120 seconds in the "thinking" block before emitting the final JSON. During this window, any network hiccup or timeout triggers a `KeyboardInterrupt` in the Python client.
- **Lesson**: We had to implement a **Persistent Tree Log** (`tree_log.json`). This allowed the orchestrator to resume exactly where it left off, turning a potential failure into a "pause/resume" workflow.

### The API JSON Extraction Struggle
- **Problem**: Early versions of the `TheoristAgent` used lazy regex `(.*?)` to extract JSON, which occasionally truncated long mathematical proposals.
- **Fix**: Switched to greedy regex `(.*)` and added fallback logic to find the first `[` and last `]` brackets.

## 2. Strategic Pivots: From Naive DFS to Priority BFS

Initially, the solver used a depth-first approach, which was prone to falling into "mathematical rabbit holes" (e.g., trying infinite series expansions for simple integrals).

### Shift to Best-First Search (BFS)
- **Decision**: We implemented a priority queue using `heapq`.
- **Heuristic**: $Priority = success\_probability \times 0.9^{depth}$.
- **Tie-breaker**: Added a counter to the priority tuple to handle cases where two paths had identical probabilities, preventing `TypeError` during heap operations.

## 3. The Precision & Verification Logic Breakthrough
The most critical bug was the "Derivation Mismatch" during verification.

### Calculus-Aware Verification
- **Problem**: The system initially checked for direct equality. However, an 'Integration' step means the *parent* is the derivative of the *child*.
- **Fix**: We modified the `orchestrator.py` to perform a "Matches Check":
    - Match 1: $Parent \approx Child$
    - Match 2: $Parent \approx \frac{d}{da}Child$ (Integration)
    - Match 3: $\frac{d}{da}Parent \approx Child$ (Differentiation)

## 4. Key Learnings
- **Integr integrand isolation**: Cleaning `Eq()` objects while preserving their structure is crucial for $I(a)$ vs $I'(a)$ logic.
- **Oracle Robustness**: The `NumericalOracle` must be modular enough to handle recursive integrals and symbolic constants like $C$.
- **Logging is Architecture**: `thinking_process.txt` isn't just a log; it's the externalized "working memory" of the system that allows the user to audit the AI's internal derivation without clogging the terminal.
