import os
from openai import OpenAI
import base64
import json
from dotenv import load_dotenv

load_dotenv()

class ReporterAgent:
    """
    Agent D: The Reporter
    Model: DeepSeek-R1 (Reasoning Model) or GPT-4o
    Role: Project Reporting & Academic Writing
    """
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        self.system_prompt = (
            "You are a professional scientific technical writer and research coordinator.\n"
            "Your task is to compile a comprehensive project report or academic-style paper based on the research process of the NeuroSymbolic Physics Solver.\n"
            "CRITICAL RULES:\n"
            "1. STRUCTURE: Include Title, Abstract, Problem Definition, Methodology (Multi-agent approach), Iteration History (Breakthroughs and Failures), Final Solution, and Conclusion.\n"
            "2. FORMAT: Output in well-formatted Markdown. Use LaTeX for mathematical formulas.\n"
            "3. INSIGHT: Analyze the STEP-WISE derivation chain. Explain how each atomic transformation (e.g., substitution, differentiation) contributes to simplifying the problem.\n"
            "4. PRECISION: Ensure all mathematical expressions are consistent with the final verified result.\n"
            "5. DIAGRAMS: Include a Mermaid flowchart (```mermaid ... ```) that represents the REASONING TREE. \n"
            "   - Visualize the derivation as a sequence of states (nodes) and transformations (edges).\n"
            "   - Group related attempts using subgraphs.\n"
            "   - Highlight the 'Critical Path' that led to the solution.\n"
            "   - CRITICAL: Wrap all node labels in double quotes (e.g., node_id[\"Label Text\"]).\n"
            "6. LANGUAGE: You MUST write the report in the language specified by the user (e.g., Chinese, English).\n"
        )

    def generate_report(self, problem_definition, tree_log, thinking_process_path, final_solution=None, language="English", image_paths=None):
        if not self.api_key:
            return "Error: DeepSeek API Key not found. Cannot generate report."

        print(f"[Reporter] Compiling final project report in {language} for: {problem_definition['name']}...")

        # Read the thinking process log
        try:
            with open(thinking_process_path, "r", encoding='utf-8') as f:
                # Limit thinking process if it's too large (e.g., last 20,000 characters)
                thinking_process = f.read()
                if len(thinking_process) > 20000:
                    thinking_process = "... [Truncated] ...\n" + thinking_process[-20000:]
        except Exception as e:
            thinking_process = f"Error reading thinking process: {e}"

        prompt = (
            f"Problem Definition: {json.dumps(problem_definition, indent=2)}\n\n"
            f"Iterative Tree Log (Path History): {json.dumps(tree_log, indent=2)}\n\n"
            f"Final Solution (if achieved): {json.dumps(final_solution, indent=2) if final_solution else 'Not achieved'}\n\n"
            f"Thinking Process Snippet:\n{thinking_process}\n\n"
            f"REQUIRED LANGUAGE: {language}\n\n"
            f"Based on the above data, write a detailed research report in {language}. Highlight the neurosymbolic collaboration between 'Theorist', 'Coder', and 'Verifier' agents."
            f" If images are provided, analyze them and incorporate your findings into the report, discussing the physics implications of the visual data."
        )

        user_content = prompt
        if image_paths:
            user_content = [{"type": "text", "text": prompt}]
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        with open(img_path, "rb") as img_file:
                            base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                        # Infer mime type from extension
                        mime_type = "image/png" if img_path.lower().endswith('.png') else "image/jpeg"
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        print(f"[Reporter] Warning: Could not read image {img_path}. Error: {e}")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat", # Using deepseek-chat (v3) for writing, or deepseek-reasoner if preferred
                messages=messages,
                stream=False
            )
            report_content = response.choices[0].message.content
            
            report_filename = f"report_{problem_definition['name'].replace(' ', '_')}.md"
            with open(report_filename, "w", encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"[Reporter] Report generated successfully: {report_filename}")
            return report_filename
        except Exception as e:
            print(f"[Reporter] Error generating report: {e}")
            return None
