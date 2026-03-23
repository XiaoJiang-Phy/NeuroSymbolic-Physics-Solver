import os
import sys
from openai import OpenAI
import json
from dotenv import load_dotenv
from utils.logger import log_thinking

load_dotenv()

class TheoristAgent:
    """
    Agent A: The Theorist
    Model: DeepSeek-R1 (Reasoning Model)
    Role: Symbolic & Mathematical Reasoning
    """
    def __init__(self):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com" # Default DeepSeek API URL
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        self.system_prompt = (
            "You are a rigorous theoretical physicist specializing in Condensed Matter Physics (CMP) and Quantum Field Theory (QFT).\n"
            "Your goal is to perform an ATOMIC symbolic derivation step-by-step for a physical system (e.g., Many-body Hamiltonians, Green's Functions, Topological Invariants).\n"
            "CMP CAPABILITIES:\n"
            "1. OPERATOR ALGEBRA: Use sympy.physics.quantum for operators. Use `Commutator(A, B)` and `AntiCommutator(A, B)`. For Fermions/Bosons, represent them as non-commutative symbols (e.g., `Symbol('c_k', commutative=False)`) or use `FermionOp`/`BosonOp` if explicitly needed. Use `Dagger(A)` for adjoints.\n"
            "2. MATRIX MECHANICS: Support Pauli matrices (`sigma_x`, `sigma_y`, `sigma_z` as non-commutative symbols or proper matrices) and Spinor bases. Represent effective models (e.g., Schrieffer-Wolff) using stepwise unitary transformations.\n"
            "3. LATTICE TRANSFORMATIONS: Perform Fourier transforms from real-space to k-space.\n"
            "4. GREEN'S FUNCTIONS & DOS: Derive Spectral Functions and DOS.\n"
            "5. MATSUBARA ENGINEERING: Perform discrete Matsubara summations to continuous frequency analytic continuations using the Cauchy residue theorem.\n"
            "6. DIAGRAMMATIC REASONING: Translate Feynman diagram rules into formal self-energy integrals and self-consistent Gap equations.\n"
            "7. RENORMALIZATION GROUP (RG): Perform Wilsonian mode elimination (fast/slow modes), field rescaling, and deriving coupling beta-functions.\n"
            "8. UNIT ENGINEERING: Enforce retention of physical constants (`hbar`, `k_B`, `e`, `m_e`) in derivations. Ensure dimensional consistency.\n"
            "CRITICAL RULES:\n"
            "1. ATOMIC STEPS: Each proposal must represent EXACTLY ONE mathematical or physical transformation.\n"
            "2. STATE TRACKING: Always output the NEW mathematical form resulting from your transformation.\n"
            "3. CLEAN SYMPY CODE: The 'sympy_code' field must contain ONLY pure SymPy code. It will be evaluated with `Commutator`, `AntiCommutator`, `Dagger`, `hbar`, `k_B`, `e`, `m_e` available in the namespace.\n"
            "4. MULTI-PATH EXPLORATION: Propose exactly 3 DIFFERENT next-step actions to explore the reasoning tree.\n"
            "5. PHYSICS AUDIT: Ensure every step satisfies causality (Im[G] >= 0) and conservation laws. If a step leads to a non-physical state, discard it.\n"
            "6. OUTPUT FORMAT: Output a JSON ARRAY of 3 objects. Each object must contain:\n"
            "   - 'action_type': The transformation applied.\n"
            "   - 'logic': Detailed physical reasoning mapping to physics_audit decision logs.\n"
            "   - 'intermediate_expression': The LaTeX string of the NEW expression.\n"
            "   - 'sympy_code': Pure SymPy string representing the NEW state.\n"
            "   - 'is_terminal': Boolean, True if this step results in the final target quantity.\n"
            "   - 'success_probability': Confidence (0.0 to 1.0).\n"
            "   - 'simplicity_score': Rank 1 to 10."
        )

    def solve(self, problem_definition, context=None):
        if not self.api_key:
            return {"error": "DeepSeek API Key not found. Please set DEEPSEEK_API_KEY."}

        print(f"[Theorist] Strategizing for: {problem_definition['name']} using DeepSeek-R1...")
        
        # System prompt reinforced for "Think then Plan" behavior
        refined_prompt = (
            f"{self.system_prompt}\n"
            "INSTRUCTION: Use your internal reasoning to explore the mathematical space. "
            "Once you have a sound strategy for the NEXT step, stop your internal derivation and "
            "output the JSON ARRAY of exactly 3 different paths. Do NOT output a final solution if verification is needed."
        )

        messages = [
            {"role": "system", "content": refined_prompt},
            {"role": "user", "content": f"Problem: {json.dumps(problem_definition)}\nContext: {json.dumps(context if context else {})}"}
        ]
        
        response_stream = self.client.chat.completions.create(
            model="deepseek-reasoner", # DeepSeek-R1
            messages=messages,
            stream=True
        )
        
        full_content = ""
        reasoning_content = ""
        
        print(f"\n--- [Theorist Thinking] (Redirected to thinking_process.txt) ---")
        
        log_thinking(f"\n\n--- Iteration Strategy Start ---\n")
        for chunk in response_stream:
            delta = chunk.choices[0].delta
            
            # Write reasoning to file
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                log_thinking(delta.reasoning_content)
                reasoning_content += delta.reasoning_content
            
            # Print final instructions (JSON) to terminal for orchestration visibility
            if delta.content:
                if not full_content:
                    print("\n--- [Theorist Final Strategy JSON] ---")
                print(delta.content, end="", flush=True)
                full_content += delta.content
        print("\n")
        
        import re
        try:
            text = full_content
            # Try to extract the JSON array cleanly
            match = re.search(r'```(?:json)?\s*(\[.*\])\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                start = text.find('[')
                end = text.rfind(']')
                if start != -1 and end != -1:
                    text = text[start:end+1]
            return json.loads(text)
        except Exception as e:
            print(f"[Theorist] Error parsing JSON: {e}")
            return {
                "symbolic_derivation": full_content,
                "error": "Failed to parse JSON"
            }
