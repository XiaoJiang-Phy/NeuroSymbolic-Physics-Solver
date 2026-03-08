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
            "1. NO JUMPING: Even if you know the final answer (e.g., Bessel or Sine Integral), do NOT propose it yet. "
            "Propose the first atomic transformation (e.g., substitute x = cos(t), use even symmetry, or partial fractions).\n"
            "2. ATOMIC STEP: Focus exclusively on ONE transformation per iteration. Change the integrand structure exactly once.\n"
            "3. SINGULARITY CHECK: Specifically address how your single step affects the point t = +/- 1.\n"
            "4. OUTPUT FORMAT: A JSON object in a markdown code block with:\n"
            "   - 'symbolic_derivation': Description of THIS SINGLE transformation.\n"
            "   - 'analytical_expression': The NEW integral form after this single transformation.\n"
            "   - 'sympy_code': Pure SymPy to represent the NEW integrand.\n"
            "   - 'singularity_handling': How the step maintains convergence at boundaries.\n"
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
            "output the JSON plan. Do NOT output a final solution if verification is needed."
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
        
        print("\n--- [Theorist Thinking Room] ---")
        for chunk in response_stream:
            delta = chunk.choices[0].delta
            
            # Print reasoning if available
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content
            
            # Print final instructions
            if delta.content:
                if not full_content:
                    print("\n\n--- [Theorist Final Strategy JSON] ---")
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
