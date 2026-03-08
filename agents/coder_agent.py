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
            "Format your output as a JSON object with keys: 'python_script', 'plot_script'. "
            "Internal Script Rule: The generated 'python_script' MUST print the final numerical "
            "result to stdout as its VERY LAST line of output. Avoid printing other text "
            "unless necessary, and ensure the last line is a pure number."
        )

    def generate_implementation(self, symbolic_ir):
        if not self.api_key:
            return {"error": "DeepSeek API Key not found."}

        print(f"[Coder] Generating Python implementation...")
        
        prompt = f"{self.system_prompt}\n\nTheorist's IR: {json.dumps(symbolic_ir)}"
        
        response_stream = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        full_content = ""
        print("\n--- [Coder Output] ---")
        for chunk in response_stream:
            delta = chunk.choices[0].delta
            if delta.content:
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
            print(f"[Coder] Error parsing JSON response: {e}")
            return {
                "python_script": full_content,
                "error": "Failed to parse JSON"
            }
