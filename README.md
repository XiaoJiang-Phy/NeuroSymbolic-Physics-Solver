# NeuroSymbolic-Physics-Solver

A multi-agent, stateful tree-based orchestration system designed to solve complex physics and mathematics problems (integrals, ODEs, etc.) using a combination of symbolic reasoning and numerical verification.

## Core Architecture

The system utilizes three specialized agents powered by DeepSeek models to iteratively derive solutions:

1.  **Agent A: The Theorist (DeepSeek-R1)**
    *   **Role**: Symbolic & Mathematical Reasoning.
    *   **Priors**: Guided by physics-specific priors (Asymptotic Matching, Singularity First, Dimensional Consistency).
    *   **Sampling**: Generates 3 differentiated mathematical paths per iteration.

2.  **Agent B: The Coder (DeepSeek-V3)**
    *   **Role**: Implementation & Interoperability.
    *   **Safeguards**: Implements **Early Exit** mechanisms via point sampling (comparing with Numerical Oracle) to prune invalid branches before expensive full integrations.

3.  **Agent C: The Verifier (DeepSeek-V3)**
    *   **Role**: Execution, Critique, and Pruning.
    *   **Fail Analyzer**: Categorizes failures into **Type A** (Algebraic errors) and **Type B** (Strategy/Singularity errors) to provide precise feedback.

4.  **Agent D: The Reporter (DeepSeek-V3)**
    *   **Role**: Project Reporting & Academic Writing.
    *   **Goal**: Compiles a comprehensive research paper or report in Markdown/LaTeX after a solution is verified or the project cycle completes. Analysis includes failure post-mortems and breakthrough summaries.

## Key Features

-   **Stateful Tree Orchestration**: Maintains a `TreeLog` of all attempted paths to prevent redundant work and enable "knowledge accumulation" across restarts.
-   **Context Pruning**: Automatically deletes failed intermediate code to maintain a clean workspace and minimize context noise for the agents.
-   **Numerical Oracle**: Uses high-precision `mpmath` (up to 50+ dps) to provide ground-truth baseline values for validation.
-   **Thinking Logs**: All detailed reasoning chains from R1 and agent critiques are redirected to `thinking_process.txt` for transparent debugging without cluttering the terminal.

## Getting Started

### Prerequisites

-   Python 3.10+
-   `mpmath`, `sympy`, `openai`, `matplotlib`, `python-dotenv`

### Installation

1.  Clone the repository.
2.  Set up your environment variables in a `.env` file:
    ```bash
    DEEPSEEK_API_KEY=your_key_here
    ```

### Running the Solver

Execute the main orchestrator to start the derivation loop:

```bash
python orchestrator.py
```

## Project Structure

-   `orchestrator.py`: The central loop controller and tree manager.
-   `agents/`: Contains the system instructions and logic for Theorist, Coder, Verifier, and Reporter.
-   `utils/numerical_oracle.py`: High-precision numerical evaluation engine.
-   `tree_log.json`: (Generated) Persistent record of historical attempts and verdicts.
-   `thinking_process.txt`: (Generated) Detailed log of AI reasoning and execution traces.
-   `report_*.md`: (Generated) Detailed research reports and final papers.

## License
MIT
