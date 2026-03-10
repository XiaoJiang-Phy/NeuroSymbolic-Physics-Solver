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
            "Your goal is to SIMPLIFY an integral or TRANSFORM it into a known form. Do NOT solve it in one go.\n"
            "CRITICAL RULES:\n"
            "1. ATOMIC STEPS: Each proposal must represent EXACTLY ONE mathematical operation (e.g., Variable Substitution, Partial Fraction Decomposition, Differentiation under the Integral Sign).\n"
            "2. STATE TRACKING: Always output the NEW mathematical form resulting from your transformation. The new state MUST be mathematically equivalent to the previous state.\n"
            "3. CLEAN SYMPY CODE: The 'sympy_code' field must contain ONLY the mathematical expression, NOT an assignment (like 'f(x, a) = ...'). If the step is an equation transformation, use 'Eq(lhs, rhs)'.\n"
            "4. MULTI-PATH EXPLORATION: Propose exactly 3 DIFFERENT next-step actions to explore the reasoning tree.\n"
            "5. OUTPUT FORMAT: Output a JSON ARRAY of 3 objects. Each object must contain:\n"
            "   - 'action_type': The transformation applied (e.g., 'Substitution', 'Integration_by_Parts').\n"
            "   - 'logic': Detailed mathematical reasoning for why this step is VALID and why it simplifies the problem.\n"
            "   - 'intermediate_expression': The LaTeX string of the NEW expression after the step.\n"
            "   - 'sympy_code': The NEW mathematical expression as a pure SymPy string.\n"
            "   - 'is_terminal': Boolean, True if this step leads directly to a known standard integral or a final closed-form solution.\n"
            "   - 'success_probability': Confidence that this step is on the optimal path (0.0 to 1.0).\n"
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
