# In jobspy/analysis/llm_analyser.py

from transformers import pipeline
import torch

# --- Initialize the local LLM pipeline ---
# We use a 'text2text-generation' pipeline with a well-regarded, instruction-tuned model.
# google/flan-t5-base is a great balance of performance and size for local execution.
# This will download the model from the Hugging Face Hub on the first run.
print("Initializing local LLM for skill analysis (google/flan-t5-base)...")
llm_pipeline = pipeline(
    "text2text-generation",
    model="google/flan-t5-base",
    dtype=torch.bfloat16 # Use bfloat16 for better performance if available
)
print("LLM for skill analysis initialized.")

def extract_skills_with_llm(text: str) -> list[str]:
    """
    Uses a local LLM to analyze a text and extract skills based on a prompt.
    """
    if not text:
        return []

    # Truncate the text to fit within the model's context window (approx. 450 words for flan-t5-base)
    # This is a rough approximation; a more precise method would involve tokenizing and then truncating.
    # However, for general resume text, word count is a reasonable heuristic.
    truncated_text = ' '.join(text.split()[:450])

    # This prompt is the key. It instructs the local LLM on exactly what to do.
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
        # Generate the text containing the skills, increasing max_length for potentially longer skill lists
        raw_output = llm_pipeline(prompt, max_length=512, num_beams=3, early_stopping=True)
        
        # The output is a dictionary, we need the generated text
        skill_string = raw_output[0]['generated_text']
        
        # Post-process the comma-separated string into a clean Python list
        skills = [skill.strip() for skill in skill_string.split(',') if skill.strip()]
        
        # Return a list of unique, lowercase skills
        return list(set(skill.lower() for skill in skills))

    except Exception as e:
        print(f"An error occurred during LLM-based skill extraction: {e}")
        return []