import os
import requests
import pandas as pd

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"

REPORTS_DIR = "reports"

def ask_llm(vulnerability_text):
    prompt = f"""
You are a DevSecOps security expert.

Analyze this vulnerability and provide:
1. Risk summary
2. Fix recommendation
3. Best practice

Vulnerability:
{vulnerability_text}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()
    return data.get("response", "No recommendation generated")


def process_excel(file_path):
    print(f"Processing: {file_path}")

    try:
        df = pd.read_excel(file_path)

        recommendations = []

        for _, row in df.iterrows():
            row_text = " | ".join([str(v) for v in row.values])

            try:
                recommendation = ask_llm(row_text)
            except Exception as e:
                recommendation = f"AI Error: {str(e)}"

            recommendations.append(recommendation)

        df["AI_Fix_Recommendation"] = recommendations

        df.to_excel(file_path, index=False)

        print(f"Updated: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


for file in os.listdir(REPORTS_DIR):
    if file.endswith(".xlsx"):
        process_excel(os.path.join(REPORTS_DIR, file))
