# In jobspy/analysis/rag_generator.py

import json
from .llm_analyser import llm_pipeline # We will reuse the same LLM pipeline

def generate_rag_insights(job_document: dict, candidate_documents: list) -> list:
    """
    Takes a job and a list of top candidate documents and uses a local LLM to generate
    summaries, match scores, justifications, and interview questions.
    """
    if not job_document or not candidate_documents:
        return []

    generated_results = []
    
    job_title = job_document.get('metadata', {}).get('title', 'N/A')
    job_description = job_document.get('full_description_raw', '')

    for candidate in candidate_documents:
        candidate_name = candidate.get('metadata', {}).get('name', 'N/A')
        candidate_skills = candidate.get('metadata', {}).get('extracted_skills', [])
        candidate_text = candidate.get('full_text_raw', '')
        candidate_id = candidate.get('_id')
        
        print(f"\n--- Generating AI Insights for candidate: {candidate_name} ---")

        prompt = f"""
        You are an expert Principal Recruiter. Given the job description and the candidate's resume, perform the following tasks:
        1. Write a concise summary of the candidate's strengths and weaknesses for this specific job.
        2. Provide a Match Score from 1 to 100, where 100 is a perfect match.
        3. Write a 1-2 sentence justification for your score, citing evidence from the resume.
        4. Create 3 tailored interview questions for this candidate based on the job requirements and their resume.

        Return the result as a single, clean JSON object with the keys: "summary", "match_score", "justification", "interview_questions".
        The "interview_questions" should be an array of strings.

        JOB DESCRIPTION:
        ---
        Title: {job_title}
        Description: {job_description}
        ---

        CANDIDATE RESUME:
        ---
        Name: {candidate_name}
        Skills: {', '.join(candidate_skills)}
        Resume Text: {candidate_text}
        ---

        JSON OUTPUT:
        """

        try:
            # --- THE FIX IS HERE ---
            # 1. Replaced 'max_length' with 'max_new_tokens' to give the model more space for the output.
            # 2. Added a print statement to see the raw output for debugging.
            raw_output = llm_pipeline(prompt, max_new_tokens=512, num_beams=3, early_stopping=True)
            generated_text = raw_output[0]['generated_text']

            print("\n--- Raw LLM Output ---")
            print(generated_text)
            print("----------------------\n")
            # --- END OF FIX ---

            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                clean_json_str = generated_text[json_start:json_end]
                parsed_json = json.loads(clean_json_str)
                parsed_json['candidate_id'] = candidate_id
                generated_results.append(parsed_json)
                print(f"Successfully generated and parsed insights for {candidate_name}.")
            else:
                print(f"Warning: Could not find a valid JSON object in the LLM output for {candidate_name}.")

        except Exception as e:
            print(f"An error occurred during RAG generation for {candidate_name}: {e}")
            
    return generated_results