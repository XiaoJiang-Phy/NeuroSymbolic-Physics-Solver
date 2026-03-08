import os
import subprocess
import sys
import json
from openai import OpenAI
from mpmath import mp
from dotenv import load_dotenv

load_dotenv()

class VerifierAgent:
    """
    Agent C: The Verifier
    Model: DeepSeek-V3 (via OpenAI client)
    Role: Execution, Critique, and Pruning
    """
    def __init__(self, tolerance=1e-10):
        self.tolerance = tolerance
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        self.system_prompt = (
            "You are a mathematically rigorous and highly critical evaluator. Your task is to analyze "
            "verification results and provide critical feedback if errors exceed limits.\n"
            "- Validation Criteria: Error threshold is 1e-10.\n"
            "- Feedback Protocol: Do not fix math yourself. Explain failure modes and command prunes.\n"
            "Format your output as a JSON object with keys: 'status', 'critique', 'command'."
        )

    def verify(self, script_path, oracle_val):
        print(f"[Verifier] Running execution sandbox and comparing with Oracle...")
        
        try:
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            # Try to find the last numerical value in the output
            lines = output.splitlines()
            candidate_val = None
            for line in reversed(lines):
                try:
                    candidate_val = mp.mpf(line.strip())
                    break
                except:
                    continue
            
            if candidate_val is None:
                return {"status": "FAIL", "critique": f"Could not find a numerical result in script output: {output}"}
            
            residual = abs(candidate_val - oracle_val)
            
            if residual < self.tolerance:
                return {"status": "SUCCESS", "residual": float(residual)}
            else:
                if not self.api_key:
                    return {"status": "FAIL", "critique": "API Key missing for analysis.", "residual": float(residual)}
                
                # Use AI to explain the failure
                prompt = f"{self.system_prompt}\n\nResidual {residual} exceeds tolerance. Oracle: {oracle_val}, Candidate: {candidate_val}"
                response_stream = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                
                full_critique = ""
                print("\n--- [Verifier Critique] ---")
                for chunk in response_stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        print(delta.content, end="", flush=True)
                        full_critique += delta.content
                print("\n")
                
                return {"status": "FAIL", "critique": full_critique, "residual": float(residual)}
                
        except Exception as e:
            return {"status": "FAIL", "critique": f"Execution error: {str(e)}"}
