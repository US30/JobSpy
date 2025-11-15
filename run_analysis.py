# In run_analysis.py
from dotenv import load_dotenv
load_dotenv()
import os
from jobspy.database import process_and_store_resume , db
from jobspy.analysis.matching import find_best_resumes_for_job
from jobspy.analysis.rag_generator import generate_rag_insights

# --- CONFIGURATION ---
RESUMES_TO_PROCESS = {
    "elon_musk_01": {"name": "Elon Musk", "file": "resumes/Software Developer Resume.pdf"},
    "utkarsh_sinha": {"name": "Utkarsh Sinha", "file": "resumes/Utkarsh_Sinha.pdf"},
}
JOB_ID_TO_MATCH = "linkedin_li-4296641686" # <-- IMPORTANT: Use the Python job ID


def main():
    """ Runs the full analysis pipeline, including Phase 3 RAG generation. """
    
    print("--- Step 1: Processing and Storing Resume ---")
    # Clear the resumes collection before processing new ones
    print("Clearing existing resumes from the database...")
    db["resumes"].delete_many({})
    print("Resumes collection cleared.")

    for candidate_id, info in RESUMES_TO_PROCESS.items():
        if os.path.exists(info['file']):
            process_and_store_resume(file_path=info['file'], candidate_name=info['name'], candidate_id=candidate_id)
        else:
            print(f"Warning: Resume file not found at {info['file']}. Skipping.")
    
    print("\n" + "="*50 + "\n")

    print("--- Step 2: Finding Best Resume Matches (Hybrid Search) ---")
    search_filters = {"metadata.extracted_skills": { "$in": ["python", "java"] }}
    top_matches = find_best_resumes_for_job(job_id=JOB_ID_TO_MATCH, filters=search_filters, limit=3) # Limit to 3 for RAG
    
    if not top_matches:
        print("Could not find any matching resumes. Halting process.")
        return
        
    print("\n--- Top Hybrid Search Results (with skill filter) ---")
    for i, match in enumerate(top_matches):
        print(f"{i+1}. {match['metadata']['name']} (ID: {match['_id']}) - Score: {match['search_score']:.2%}")
    
    print("\n" + "="*50 + "\n")

    # --- NEW SECTION: Displaying Top 5 Semantic Search Results (without skill filter) ---
    print("--- Top 5 Semantic Search Results (without skill filter) ---")
    # Temporarily remove the hard filter to see all semantic matches
    all_semantic_matches = find_best_resumes_for_job(job_id=JOB_ID_TO_MATCH, filters={}, limit=5)

    if not all_semantic_matches:
        print("No semantic matches found.")
    else:
        for i, match in enumerate(all_semantic_matches):
            name = match.get('metadata', {}).get('name', 'N/A')
            print(f"{i+1}. {name} (ID: {match['_id']}) - Score: {match['search_score']:.2%}")
    
    print("\n" + "="*50 + "\n")

    # --- Step 3: Generate AI-Powered Insights (Phase 3) ---
    print("--- Step 3: Generating RAG Insights for Top Candidates ---")

    # We need the full job document for the prompt
    job_doc = db["private_jobs"].find_one({"_id": JOB_ID_TO_MATCH})
    
    # We also need the full candidate documents, not just the projected results
    top_candidate_ids = [match['_id'] for match in top_matches]
    candidate_docs = list(db["resumes"].find({"_id": {"$in": top_candidate_ids}}))
    
    # Call our new RAG function
    rag_results = generate_rag_insights(job_doc, candidate_docs)

    if rag_results:
        print("\n--- AI-Generated Recruitment Analysis ---")
        for result in rag_results:
            print(f"Candidate: {db['resumes'].find_one({'_id': result['candidate_id']})['metadata']['name']}")
            print(f"  Match Score: {result.get('match_score', 'N/A')}/100")
            print(f"  Justification: {result.get('justification', 'N/A')}")
            print("  Summary:")
            print(f"    {result.get('summary', 'N/A')}")
            print("  Interview Questions:")
            for i, q in enumerate(result.get('interview_questions', [])):
                print(f"    {i+1}. {q}")
            print("-" * 30)

if __name__ == "__main__":
    main()