import os
import time

def log_thinking(content, filename="thinking_process.txt"):
    """
    Safely append content to the thinking process log file with retries for Windows permission issues.
    """
    max_retries = 5
    for i in range(max_retries):
        try:
            with open(filename, "a", encoding='utf-8') as f:
                f.write(content)
            break
        except PermissionError:
            if i < max_retries - 1:
                time.sleep(0.1)
            else:
                print(f"[Warning] Could not write to {filename} due to permission error.")
