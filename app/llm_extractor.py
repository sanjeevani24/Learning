import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def extract_person_details(text):

    prompt = f"""
Extract the following information from the OCR text.

Return ONLY valid JSON.

{{
    "full_name": "",
    "gender": "",
    "address": ""
}}

OCR TEXT:
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a KYC document parser. Return only JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content

    print("GROQ RESPONSE:")
    print(content)

    print("========== GROQ RESPONSE ==========")
    print(repr(content))
    print("===================================")


    content = response.choices[0].message.content.strip()

    # Handle markdown wrapped JSON
    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    return json.loads(content)