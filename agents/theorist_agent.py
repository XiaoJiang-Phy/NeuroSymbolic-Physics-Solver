import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

class TheoristAgent:
    """
    Agent A: The Theorist
    Model: DeepSeek-R1 (Reasoning Model)
    Role: Symbolic & Mathematical Reasoning
    """
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com" # Default DeepSeek API URL
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        self.system_prompt = (
            "You are a rigorous theoretical physicist performing an ATOMIC symbolic derivation step-by-step.\n"
            "CRITICAL RULES:\n"
            "1. OPERATOR SET: You must choose from one of the following paths: [Parametric_Differentiation, Basis_Expansion, Contour_Integration, Symmetry_Reduction].\n"
            "2. PHYSICS PRIORS:\n"
            "   - Asymptotic Matching: In your derivation, you MUST compute and mention the asymptotic behavior at extreme limits (e.g. N->1, N->infinity). Discard branches that fail asymptotic limits.\n"
            "   - Singularity First: Do NOT perform series expansion without resolving 0/0 singularities first.\n"
            "   - Dimensional Consistency: Verify that physical weights and dimensions remain consistent in each step.\n"
            "3. MULTI-PATH SAMPLING: You must propose exactly 3 DIFFERENT paths simultaneously.\n"
            "4. OUTPUT FORMAT: Output a JSON ARRAY of exactly 3 objects in a markdown code block. Each object must have:\n"
            "   - 'path_type': One of the allowed operators (e.g. 'Parametric_Differentiation').\n"
            "   - 'symbolic_derivation': Description of THIS SINGLE transformation.\n"
            "   - 'analytical_expression': The NEW integral form after this single transformation.\n"
            "   - 'sympy_code': Pure SymPy to represent the NEW integrand.\n"
            "   - 'success_probability': Your predicted confidence in this path (0.0 to 1.0).\n"
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
        
        reasoning_log = "thinking_process.txt"
        print(f"\n--- [Theorist Thinking] (Redirected to {reasoning_log}) ---")
        
        with open(reasoning_log, "a", encoding='utf-8') as log_f:
            log_f.write(f"\n\n--- Iteration Strategy Start ---\n")
            for chunk in response_stream:
                delta = chunk.choices[0].delta
                
                # Write reasoning to file
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    log_f.write(delta.reasoning_content)
                    log_f.flush()
                    reasoning_content += delta.reasoning_content
                
                # Print final instructions (JSON) to terminal for orchestration visibility
                if delta.content:
                    if not full_content:
                        print("\n--- [Theorist Final Strategy JSON] ---")
                    print(delta.content, end="", flush=True)
                    full_content += delta.content
        print("\n")
        
        try:
            text = full_content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            print(f"[Theorist] Error parsing JSON: {e}")
            return {
                "symbolic_derivation": full_content,
                "error": "Failed to parse JSON"
            }
