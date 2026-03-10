import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

try:
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[{"role": "user", "content": "1+1="}],
        max_tokens=10
    )
    print(f"Success: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
