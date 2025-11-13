# In jobspy/analysis/llm_analyser.py

import openai
import os
from dotenv import load_dotenv

load_dotenv()

# --- Initialize the Azure OpenAI client ---
if "AZURE_OPENAI_ENDPOINT" not in os.environ or "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError("AZURE_OPENAI_ENDPOINT and OPENAI_API_KEY environment variables not found.")

client = openai.AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["OPENAI_API_KEY"],
    api_version=os.environ.get("OPENAI_API_VERSION", "2025-04-01-preview")
)

def extract_skills_with_llm(text: str) -> list[str]:
    """
    Uses the Azure OpenAI API to analyze a text and extract skills based on a prompt.
    """
    if not text:
        return []

    prompt = f"""
    Based on the following resume text, extract all of the technical skills, programming languages, and software tools mentioned.
    Return the skills as a single, comma-separated list. For example: Python, React, SQL, AWS, Docker.

    Resume Text:
    ---
    {text}
    ---
    
    Extracted Skills:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts skills from text."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=256,
        )
        
        skill_string = response.choices[0].message.content
        
        # Post-process the comma-separated string into a clean Python list
        skills = [skill.strip() for skill in skill_string.split(',') if skill.strip()]
        
        # Return a list of unique, lowercase skills
        return list(set(skill.lower() for skill in skills))

    except Exception as e:
        print(f"An error occurred during Azure OpenAI-based skill extraction: {e}")
        return []