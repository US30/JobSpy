# In run_analysis.py

import os
from jobspy.database import process_and_store_resume
from jobspy.analysis.matching import find_best_resumes_for_job

# --- CONFIGURATION ---
RESUMES_TO_PROCESS = {
    "elon_musk_01": {"name": "Elon Musk", "file": "resumes/Software Developer Resume.pdf"},
}
JOB_ID_TO_MATCH = "linkedin_li-4296641686" # <-- IMPORTANT: Use the Python job ID

def main():
    """ Runs the full, final analysis pipeline. """
    
    print("--- Step 1: Processing and Storing Resume ---")
    for candidate_id, info in RESUMES_TO_PROCESS.items():
        if os.path.exists(info['file']):
            process_and_store_resume(
                file_path=info['file'],
                candidate_name=info['name'],
                candidate_id=candidate_id
            )
        else:
            print(f"Warning: Resume file not found at {info['file']}. Skipping.")
    
    print("\n" + "="*50 + "\n")

    print("--- Step 2: Finding Best Resume Matches using Hybrid Search ---")

    # Define the hard filters for skills
    search_filters = {
        "metadata.extracted_skills": { "$in": ["python", "java"] }
    }
    
    top_matches = find_best_resumes_for_job(
        job_id=JOB_ID_TO_MATCH,
        filters=search_filters,
        limit=5
    )
    
    if top_matches:
        print("\n--- Top Matching Candidates (Hybrid Search Results) ---")
        for i, match in enumerate(top_matches):
            print(f"{i+1}. {match['metadata']['name']} (ID: {match['_id']})")
            print(f"   Semantic Search Score: {match['search_score']:.2%}")
            print(f"   Extracted Skills: {match['metadata']['extracted_skills']}")
            print("-" * 20)
    else:
        print("Could not find any matching resumes that satisfy the filters.")

if __name__ == "__main__":
    main()