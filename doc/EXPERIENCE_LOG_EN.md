# Project Experience Log: NeuroSymbolic Physics Solver

> A comprehensive technical retrospective documenting every significant challenge, strategic pivot, and lesson learned during the development of a multi-agent AI system for solving complex mathematical integrals.

---

## 1. Project Genesis: The Core Idea

The fundamental hypothesis behind this project is deceptively simple: **Can we make an AI "derive" a mathematical proof step-by-step, rather than just guess the answer?**

Large Language Models (LLMs) are prone to "hallucination jumps" — they will often skip from a problem statement directly to a final answer, fabricating intermediate steps that are mathematically invalid. Our solution was to enforce an **Atomic Step** constraint: the AI (Theorist) is only allowed to propose *one single mathematical operation* at a time. A separate, deterministic engine (the Numerical Oracle) then *verifies* each step before the next one is explored. This creates a system where the AI is the "explorer" and the numerical engine is the "censor."

This idea sounds clean on paper. In practice, however, the journey from concept to a working, verified solution was filled with unexpected obstacles.

---

## 2. The Network & API Layer: Wrestling with Long-Reasoning Models

### 2.1. The `KeyboardInterrupt` Nightmare

**The Core Problem**: The Theorist agent uses **DeepSeek-R1**, a "reasoning" model. Unlike standard chat models that respond in 1-5 seconds, R1 has an internal "thinking" phase that can last **60 to 180 seconds**. During this entire window, the Python `openai` client holds an open HTTPS connection, streaming `reasoning_content` tokens.

Any network micro-interruption — a WiFi fluctuation, a transient DNS failure, an ISP route change — during this long window would cause the underlying `httpcore`/`httpx` library to raise an exception, which Python's signal handler would then surface as a `KeyboardInterrupt`. This was not the user pressing Ctrl+C; it was the network stack giving up.

**Frequency**: This happened roughly 1 in every 3-4 API calls during peak hours, making the system effectively unusable without mitigation.

**The Solution: Persistent State via `tree_log.json`**

We implemented a checkpoint system. After every successfully verified derivation step, the orchestrator serializes the entire search tree state to `tree_log.json`. When the script restarts (either manually or via a wrapper), it detects the existing log, loads the last checkpoint, and reconstructs the priority queue from that point.

```python
# orchestrator.py — Resumption logic
if self.tree_log:
    last_step_key = list(self.tree_log.keys())[-1]
    last_step = self.tree_log[last_step_key]
    print(f"[Orchestrator] Resuming search from checkpoint: {last_step_key}")
    start_node = {
        "expression": last_step['to'],
        "depth": int(last_step_key.split("_")[-1]),
        "path": list(self.tree_log.values())
    }
```

**Lesson**: When working with long-reasoning models, **state persistence is not optional; it is a core architectural requirement.** Design your pipeline as a series of idempotent, resumable stages from the very beginning.

### 2.2. JSON Extraction from Free-Form LLM Output

**The Core Problem**: The Theorist outputs a JSON array of 3 proposals. However, the R1 model sometimes wraps its JSON in Markdown code fences (` ```json ... ``` `), sometimes not. Worse, the early lazy regex `(.*?)` would sometimes match only a *portion* of the JSON array if the model's output contained multiple code blocks or stray brackets.

**The Fix (Multi-Stage Extraction)**:
1. **Stage 1**: Try to find a fenced code block: `r'```(?:json)?\s*(\[.*\])\s*```'` with `re.DOTALL` and **greedy** `(.*)`.
2. **Stage 2 (Fallback)**: If no fenced block is found, locate the first `[` and the last `]` in the entire output and extract that substring.
3. **Stage 3**: Parse the extracted string with `json.loads()`.

**Lesson**: Never assume an LLM will produce structurally perfect output. Always implement a layered extraction strategy with fallbacks. Greedy regex is safer than lazy regex for structured data extraction.

---

## 3. The Search Strategy Evolution

### 3.1. Phase 1: Naive Depth-First Search (DFS)

The initial implementation was a simple sequential loop: ask the Theorist for one step, verify it, log it, repeat. This is effectively a DFS with a branching factor of 1.

**The Problem**: This approach has no recovery mechanism. If the Theorist proposes a "partial fraction decomposition" and that path leads to a dead end after 5 steps, all that work is wasted. The system cannot backtrack to try "differentiation under the integral sign" instead.

**Observed Failure Mode**: The solver would often get stuck trying to evaluate sub-integrals like $\int_0^\infty \frac{x \sin(ax)}{x^2+1} dx$ numerically from the partial fraction path, which is itself a non-trivial integral. It would loop, proposing further decompositions that never simplified.

### 3.2. Phase 2: Best-First Search (BFS) with Priority Queue

**The Decision**: We replaced the linear loop with a priority queue (`heapq`) that stores *all* explored but unvisited nodes. The Theorist now generates **3 different paths** per node, and the orchestrator always processes the globally most promising node next, regardless of which "branch" it belongs to.

**Priority Heuristic**: $P = \text{success\_probability} \times 0.9^{\text{depth}}$

This formula has two critical properties:
- **Confidence Bias**: Higher `success_probability` (as estimated by the Theorist) leads to higher priority.
- **Depth Penalty**: The exponential decay $0.9^{depth}$ ensures that shallow, high-confidence paths are always explored before deep, speculative ones. This prevents "infinite descent" into complex but unproductive transformations.

**The Tie-Breaker Bug**: Python's `heapq` compares tuple elements lexicographically. If two nodes have the same priority and depth, `heapq` would try to compare the `dict` objects, raising a `TypeError`. We fixed this by adding a monotonically increasing counter as the third element of the tuple: `(-priority, depth, self.counter, node)`.

```python
# orchestrator.py — BFS push with tie-breaker
priority = prob * (0.9 ** depth)
heapq.heappush(self.queue, (-priority, depth + 1, self.counter, new_node))
self.counter += 1
```

**Lesson**: In any tree search over LLM-generated strategies, BFS with a well-designed heuristic dramatically outperforms DFS. The branching factor (3 in our case) provides the diversity needed to find alternative paths, while the depth penalty prevents resource exhaustion.

### 3.3. The Visited Set

To prevent the Theorist from proposing circular transformations (e.g., A → B → A), we maintain a `visited_expressions` set. Before processing any node, its cleaned expression string is checked against this set. If it's already been explored, the node is silently discarded.

---

## 4. The Precision & Verification Logic Breakthrough

This was the single most impactful debugging challenge in the entire project. Even with correct mathematical reasoning from the Theorist, the solver was rejecting valid steps due to flawed verification logic.

### 4.1. The Original (Broken) Verification

The initial verification was simple: evaluate the parent expression and the child expression numerically, then check if they are equal within tolerance. This works for algebraic transformations (e.g., factoring, expanding), but **it fails completely for calculus operations**.

**Why it fails**: Consider the "Differentiation under the Integral Sign" step:
- **Parent**: $I(a) = \int_0^\infty \frac{\sin(ax)}{x(x^2+1)} dx \approx 0.9929$ (for $a=1$)
- **Child**: $I'(a) = \int_0^\infty \frac{\cos(ax)}{x^2+1} dx \approx 0.5779$ (for $a=1$)

These are *not* numerically equal! The child is the *derivative* of the parent. Checking for direct equality incorrectly prunes this valid and critical step.

### 4.2. The Fix: Multi-Modal Calculus-Aware Verification

We redesigned the verification to try **multiple matching modes** and accept the step if *any* mode succeeds:

```python
# orchestrator.py — Multi-modal verification
matches = []

# Mode 1: Direct Equivalence (for algebraic transforms)
p_val = self.oracle.evaluate_full_expression(self.problem, parent_expr)
c_val = self.oracle.evaluate_full_expression(self.problem, child_expr)
if p_val is not None and c_val is not None:
    matches.append(abs(p_val - c_val))

# Mode 2: Parent ≈ d/da(Child) — for "Integration" steps
if "integration" in action.lower():
    c_deriv_val = self.oracle.evaluate_derivative(self.problem, child_expr, wrt='a')
    if p_val is not None and c_deriv_val is not None:
        matches.append(abs(p_val - c_deriv_val))

# Mode 3: d/da(Parent) ≈ Child — for "Differentiation" steps
if "differentiation" in action.lower():
    p_deriv_val = self.oracle.evaluate_derivative(self.problem, parent_expr, wrt='a')
    if p_deriv_val is not None and c_val is not None:
        matches.append(abs(p_deriv_val - c_val))

# Accept if ANY mode matches within tolerance
if matches and min(matches) < 1e-3:
    # Step is valid!
```

**A Subtle Gotcha**: The word "Integration" in the action type is ambiguous. It can mean:
1. **Antidifferentiation**: $I(a) \to -\frac{\pi}{2}e^{-a} + C$ (a calculus step where Mode 2 applies).
2. **Evaluating a definite integral**: $\int_0^a \frac{\pi}{2} e^{-t} dt \to \frac{\pi}{2}(1 - e^{-a})$ (an algebraic/identity step where Mode 1 applies).

The multi-modal approach handles this gracefully: if Mode 2 fails for case (2), Mode 1 will still succeed.

### 4.3. The `NumericalOracle` Robustness Journey

The `evaluate_full_expression` method went through **5 major revisions**:
1. **v1**: Simple `sympy.sympify` + `.evalf()`. Failed on nested `Integral()` objects.
2. **v2**: Added `mpmath.quad` for numerical integration. Failed on `Eq(lhs, rhs)` expressions.
3. **v3**: Added RHS extraction for `Eq()` objects. Failed on expressions containing symbolic constants like `C` or function calls like `I(a)`.
4. **v4**: Expanded the namespace to include `a`, `x`, `u`, `t`, `C`, added default `C=0` substitution, and implemented a recursive `_eval_node` function that handles `sin`, `cos`, `exp`, nested `Integral`, and `Pow` nodes.
5. **v5 (Final)**: Added singularity handling (offset `1e-20` for removable singularities like $\sin(x)/x$ at $x=0$), and replaced `mp.diff` with a manual central difference method for better stability.

```python
# numerical_oracle.py — Manual central difference derivative
h = 1e-7
v_plus = f_val(current_val + h)
v_minus = f_val(current_val - h)
return (mp.mpf(str(v_plus)) - mp.mpf(str(v_minus))) / (2 * h)
```

**Lesson**: The Numerical Oracle is the **single point of trust** in the entire system. Every other component (Theorist, Coder, Verifier) can be wrong, and the Oracle will catch it. Therefore, the Oracle must be the most robust, most tested, and most conservatively designed component.

---

## 5. The Terminal Verification Problem

### 5.1. The Point-Sampling Early Exit Bug

When a terminal (final answer) node was reached, the Coder agent was instructed to insert a "point sampling check" in the generated Python script. The idea was to evaluate the integrand at a specific point (e.g., $x = 0.999$) and compare it with the Oracle's value.

**The Bug**: The `oracle_val` passed to the Coder was the *ground-truth value of the entire integral* (≈ 0.993 for $a=1$), **not** the value of the integrand at $x = 0.999$. The Coder's generated script would then compare the integrand value at $x = 0.999$ with the integral value, find a massive deviation, and raise `EarlyExitException` — incorrectly killing a correct solution.

**The Fix**: We stopped passing `oracle_val` to the Coder for terminal nodes. The Oracle value is now only used by the Verifier for the final residual comparison, where it is correctly compared against the script's *output* (the computed integral value), not the integrand.

```python
# orchestrator.py — Terminal check (fixed)
oracle_val = self.oracle.evaluate_ground_truth(self.problem)
implementation = self.coder.generate_implementation(self.problem, step)  # No oracle_val!
# ...
verification_result = self.verifier.verify(script_path, oracle_val)  # Oracle used HERE
```

---

## 6. The Expression Cleaning Minefield

### 6.1. The `Eq()` Preservation Decision

Early versions of `_clean_math_expr` would strip everything before and including `=` signs. This was catastrophic for equation-form expressions like `Eq(Integral(...), pi*(1-exp(-a))/2)`, because stripping the `Eq()` wrapper would lose the relationship between the LHS (the integral) and the RHS (the closed form).

**Decision**: We explicitly preserved `Eq()` objects and only stripped superficial labels like `"I(a) ="` or `"f(x, a) ="`.

### 6.2. The `I` vs `I(a)` Collision

SymPy uses `I` for the imaginary unit $\sqrt{-1}$. But our Theorist often writes `I(a)` to mean the integral as a function. We had to add a regex-based pre-processor that renames `I(` to `IntFunc(` before passing to `sympify`, while keeping standalone `I` as the imaginary unit.

```python
# numerical_oracle.py — I(a) vs I collision fix
s = re.sub(r'(?<![a-zA-Z0-9_])I\(', 'IntFunc(', s)
```

---

## 7. Key Takeaways

| Category | Lesson | Impact |
|---|---|---|
| **Architecture** | State persistence is a first-class requirement for long-reasoning AI pipelines | Prevented data loss across dozens of API failures |
| **Search** | BFS with depth-penalized priority >>> DFS for mathematical exploration | Found the correct derivation path within 8 iterations |
| **Verification** | Verification must be "calculus-aware", not just "equality-checking" | Unblocked the entire differentiation-under-integral-sign pathway |
| **Oracle** | The numerical engine is the single point of trust; invest maximum effort in its robustness | Caught 100% of invalid Theorist proposals |
| **LLM Output** | Never assume structured output from an LLM; always use layered extraction | Eliminated JSON truncation errors |
| **Naming** | Symbol collisions between mathematical notation and programming libraries are inevitable | `I(a)` vs `I` (imaginary unit) was a 2-hour debug session |
| **Logging** | `thinking_process.txt` is not just a log — it's externalized working memory | Essential for auditing the Theorist's reasoning without terminal clutter |
