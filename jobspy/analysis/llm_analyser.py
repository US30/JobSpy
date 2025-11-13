# In jobspy/analysis/llm_analyser.py

import openai
import os

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

<<<<<<< Updated upstream
    # Truncate the text to fit within the model's context window (approx. 450 words for flan-t5-base)
    # This is a rough approximation; a more precise method would involve tokenizing and then truncating.
    # However, for general resume text, word count is a reasonable heuristic.
    truncated_text = ' '.join(text.split()[:450])

    # This prompt is the key. It instructs the local LLM on exactly what to do.
=======
>>>>>>> Stashed changes
    prompt = f"""
    Based on the following resume text, extract all of the technical skills, programming languages, and software tools mentioned.
    Return the skills as a single, comma-separated list. For example: Python, React, SQL, AWS, Docker.

    Resume Text:
    ---
    {truncated_text}
    ---
    
    Extracted Skills:
    """

    try:
<<<<<<< Updated upstream
        # Generate the text containing the skills, increasing max_length for potentially longer skill lists
        raw_output = llm_pipeline(prompt, max_length=512, num_beams=3, early_stopping=True)
=======
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts skills from text."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=256,
        )
>>>>>>> Stashed changes
        
        skill_string = response.choices[0].message.content
        
        # Post-process the comma-separated string into a clean Python list
        skills = [skill.strip() for skill in skill_string.split(',') if skill.strip()]
        
        # Return a list of unique, lowercase skills
        return list(set(skill.lower() for skill in skills))

    except Exception as e:
        print(f"An error occurred during Azure OpenAI-based skill extraction: {e}")
        return []