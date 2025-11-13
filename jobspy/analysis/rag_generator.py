# In jobspy/analysis/rag_generator.py

import json
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

def generate_rag_insights(job_document: dict, candidate_documents: list) -> list:
    """
    Takes a job and a list of top candidate documents and uses the Azure OpenAI API to generate
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
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "You are an expert Principal Recruiter providing hiring analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                max_completion_tokens=512,
            )
            
            generated_text = response.choices[0].message.content

            print("\n--- Raw Azure OpenAI Output ---")
            print(generated_text)
            print("----------------------\n")

<<<<<<< Updated upstream
            clean_json_str = ""
            # Attempt to find JSON within markdown code blocks first
            json_block_start = generated_text.find('```json')
            json_block_end = generated_text.rfind('```')

            if json_block_start != -1 and json_block_end != -1 and json_block_start < json_block_end:
                clean_json_str = generated_text[json_block_start + len('```json'):json_block_end].strip()
            else:
                # Fallback to finding the first '{' and last '}'
                json_start = generated_text.find('{')
                json_end = generated_text.rfind('}') + 1
                if json_start != -1 and json_end != -1 and json_start < json_end:
                    clean_json_str = generated_text[json_start:json_end].strip()

            if clean_json_str:
                parsed_json = json.loads(clean_json_str)
                parsed_json['candidate_id'] = candidate_id
                generated_results.append(parsed_json)
                print(f"Successfully generated and parsed insights for {candidate_name}.")
            else:
                print(f"Warning: Could not find a valid JSON object in the LLM output for {candidate_name}.")
=======
            parsed_json = json.loads(generated_text)
            parsed_json['candidate_id'] = candidate_id
            generated_results.append(parsed_json)
            print(f"Successfully generated and parsed insights for {candidate_name}.")
>>>>>>> Stashed changes

        except Exception as e:
            print(f"An error occurred during RAG generation for {candidate_name}: {e}")
            
    return generated_results