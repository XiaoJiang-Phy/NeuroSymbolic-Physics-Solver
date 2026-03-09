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
            "- Multi-point Verification (Consistency Check): Determine if the formula diverges at a singularity. "
            "Set `is_divergent_at_singularity` to True/False based on your analysis.\n"
            "   - Type A (Algebraic error): Formula structure is likely correct but there is an algebraic mistake (coefficients/symbols). Recommend Coder to fix coefficients.\n"
            "   - Type B (Strategy error): Singularities lead to divergence, or basis lacks analytic properties. Recommend forcing a change of basis (e.g., switch to Gegenbauer polynomials).\n"
            "- Feedback Protocol: Return a JSON object containing keys:\n"
            "   - 'is_divergent_at_singularity' (boolean)\n"
            "   - 'insight' (string explaining the error, e.g., 'Integration diverges at t=1, try parameter substitution.')"
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
                
                reasoning_log = "thinking_process.txt"
                print(f"--- [Verifier Critique] (Redirected to {reasoning_log}) ---")
                
                full_critique = ""
                with open(reasoning_log, "a", encoding='utf-8') as log_f:
                    log_f.write(f"\n\n--- Verifier Critique Start ---\n")
                    for chunk in response_stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            log_f.write(delta.content)
                            log_f.flush()
                            full_critique += delta.content
                print("[Verifier] Critique generated.\n")
                
                import re
                try:
                    text_to_parse = full_critique
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_to_parse, re.DOTALL)
                    if match:
                        text_to_parse = match.group(1)
                    else:
                        start = text_to_parse.find('{')
                        end = text_to_parse.rfind('}')
                        if start != -1 and end != -1:
                            text_to_parse = text_to_parse[start:end+1]
                    critique_data = json.loads(text_to_parse)
                    
                    is_divergent = critique_data.get("is_divergent_at_singularity", False)
                    insight = critique_data.get("insight", "Numerical deviation.")
                    
                    error = residual
                    threshold = self.tolerance
                    
                    if error > threshold:
                        verdict_type = "Type B" if is_divergent else "Type A"
                        return {
                            "status": "FAIL",
                            "verdict": f"Branch Failed. Classification: {verdict_type}. Insight: {insight}",
                            "prune_branch": True,
                            "residual": float(residual)
                        }
                except Exception as e:
                    return {"status": "FAIL", "verdict": "Branch Failed. Could not parse JSON critique.", "prune_branch": True}
                
        except subprocess.CalledProcessError as e:
            output = e.stdout + e.stderr
            if "EarlyExitException" in output or "deviation >" in output.lower() or "early exit" in output.lower():
                return {"status": "FAIL", "verdict": "Branch Failed. Classification: Early Exit requested by sampling point check.", "prune_branch": True}
            else:
                return {"status": "FAIL", "verdict": f"Execution error: {e.stderr.strip()}", "prune_branch": True}
        except Exception as e:
            return {"status": "FAIL", "verdict": f"Execution error: {str(e)}", "prune_branch": True}
