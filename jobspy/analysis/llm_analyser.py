# In jobspy/analysis/llm_analyser.py

import os
import json
import re
from openai import AzureOpenAI

# --- This file relies on the .env file being loaded by the main script ---

required_vars = ["AZURE_OPENAI_ENDPOINT", "OPENAI_API_KEY", "OPENAI_DEPLOYMENT_NAME"]
if not all(var in os.environ for var in required_vars):
    raise EnvironmentError(
        "CRITICAL ERROR: Please set AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, and OPENAI_DEPLOYMENT_NAME in your .env file."
    )

try:
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["OPENAI_API_KEY"],
        api_version=os.environ.get("OPENAI_API_VERSION", "2024-02-01")
    )
    print("Azure OpenAI client initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize Azure OpenAI client. Check credentials/library version. Error: {e}")
    client = None

def _extract_relevant_sections(text: str) -> str:
    """
    A helper function to extract only the most important sections from a resume
    to create a smaller, more focused prompt for the LLM.
    """
    section_keywords = ["skills", "experience", "projects", "education", "summary", "objective"]
    pattern = re.compile(r'^\s*(' + '|'.join(section_keywords) + r')\s*:', re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return text[:4000]
    extracted_text = ""
    for i, match in enumerate(matches):
        start_pos = match.start()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
        section_content = text[start_pos:end_pos].strip()
        extracted_text += section_content + "\n\n"
    return extracted_text.strip()

def extract_skills_with_llm(text: str) -> list[str]:
    """
    Uses the Azure OpenAI API to analyze a text and extract skills based on a prompt.
    """
    if not client or not text:
        return []

    print("Extracting relevant sections from resume for a smaller prompt...")
    relevant_text = _extract_relevant_sections(text)

    prompt = f"""
    Analyze the following resume text and extract all technical skills, programming languages, and software tools.
    Respond with a single, comma-separated string of the skills you find.

    Resume Text:
    ---
    {relevant_text} 
    ---
    """

    try:
        print("Extracting skills with Azure OpenAI model...")
        response = client.chat.completions.create(
            model=os.environ["OPENAI_DEPLOYMENT_NAME"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts skills from text."},
                {"role": "user", "content": prompt}
            ],
            # --- THE FINAL, DEFINITIVE FIX IS HERE, BASED ON YOUR CORRECTIONS ---
            max_completion_tokens=512, # The correct parameter name
            # Removed the unsupported 'temperature' parameter
        )
        
        # We will keep this for one final confirmation.
        print("\n--- Full Raw API Response ---")
        print(response)
        print("---------------------------\n")
        
        skill_string = response.choices[0].message.content or ""
        
        print(f"Raw skills output from model: '{skill_string}'")
        
        finish_reason = response.choices[0].finish_reason
        if finish_reason == 'length':
            print("CRITICAL WARNING: The model output was cut off.")
            
        if not skill_string:
             print("CRITICAL WARNING: The model returned an empty string.")
             return []

        skills = [skill.strip() for skill in skill_string.split(',') if skill.strip()]
        
        return list(set(skill.lower() for skill in skills))

    except Exception as e:
        print(f"An error occurred during Azure OpenAI-based skill extraction: {e}")
        return []