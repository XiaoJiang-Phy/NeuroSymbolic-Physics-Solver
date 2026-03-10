import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

class CoderAgent:
    """
    Agent B: The Coder
    Model: DeepSeek-V3 (via OpenAI client)
    Role: Implementation & Interoperability
    """
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        self.system_prompt = (
            "You are an expert scientific computing engineer. Your task is to accurately translate "
            "'The Theorist's' mathematical strategies into executable Python code.\n"
            "- Python Implementation: Use `sympy` for symbolic manipulation and `mpmath` for "
            "50-dps high-precision numerical evaluation.\n"
            "- Strict Rule (Python Plotting): For all data visualization and residual plots, you must "
            "strictly set the matplotlib global font family to Arial (sans-serif) using "
            "plt.rcParams['font.sans-serif'] = ['Arial'].\n"
            "- Parameter Consistency: You MUST use the FIRST parameter value provided in the problem definition's 'parameters' list for your final numerical output to ensure comparison with the oracle succeeds.\n"
            "- Point Sampling & Early Exit: If an `oracle_point_val` at `t=0.999` (or `x=0.999`) is provided, you MUST insert a point sampling check before the full numerical integration. Evaluate your numerical python integrand at 0.999. If the deviation `abs(sampled - oracle_point_val) / abs(oracle_point_val)` is > 10% (0.1), you MUST explicitly throw an exception: `raise Exception('EarlyExitException: Point sampling deviation > 10%')` to stop execution.\n"
            "Format your output as a JSON object with keys: 'python_script', 'plot_script'. "
            "Internal Script Rule: The generated 'python_script' MUST print the final numerical "
            "result to stdout as its VERY LAST line of output. Avoid printing other text "
            "unless necessary, and ensure the last line is a pure number."
        )

    def generate_implementation(self, problem_definition, symbolic_ir):
        if not self.api_key:
            return {"error": "DeepSeek API Key not found."}

        print(f"[Coder] Generating Python implementation...")
        
        prompt = f"{self.system_prompt}\n\nProblem Definition: {json.dumps(problem_definition)}\n\nTheorist's IR: {json.dumps(symbolic_ir)}"
        prompt += "\n\nMandatory Requirement: Your 'python_script' MUST include a function `asymptotic_check(parameter_name)` that calculates the limit of your analytical expression as the primary parameter (usually 'a') approaches 0 or infinity (specify which one makes sense for the physics of the problem). The script MUST print the result of this limit evaluation. The Verifier will handle the comparison."
        
        response_stream = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        full_content = ""
        reasoning_log = "thinking_process.txt"
        print(f"\n--- [Coder Generating] (Redirected to {reasoning_log}) ---")
        
        with open(reasoning_log, "a", encoding='utf-8') as log_f:
            log_f.write(f"\n\n--- Coder Implementation Start ---\n")
            for chunk in response_stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    log_f.write(delta.content)
                    log_f.flush()
                    full_content += delta.content
        print("[Coder] Implementation generated.\n")
        
        import re
        try:
            text = full_content
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    text = text[start:end+1]
            return json.loads(text)
        except Exception as e:
            print(f"[Coder] Error parsing JSON response: {e}")
            return {
                "python_script": full_content,
                "error": "Failed to parse JSON"
            }
