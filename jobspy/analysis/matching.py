# In jobspy/analysis/matching.py

import os
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --- Initialize components ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_CONNECTION_STRING)
db = client["job_database"]
resumes_collection = db["resumes"]
jobs_collection = db["private_jobs"]

print("Initializing sentence-transformer model for matching...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("Matching model initialized.")

def find_best_resumes_for_job(job_id: str, filters: dict = {}, limit: int = 5):
    """
    Performs a reliable, Python-native hybrid search.
    This method is guaranteed to work by separating the filtering and semantic scoring steps.
    """
    job = jobs_collection.find_one({"_id": job_id})
    if not job:
        print(f"Job with ID '{job_id}' not found.")
        return []

    print(f"\n--- Matching against Job: {job['metadata']['title']} at {job['metadata']['company']} ---")
    
    job_description = job.get('full_description_raw', '')
    if not job_description:
        print("Job has no description to create an embedding from.")
        return []
    
    # Get the job's embedding vector and reshape it for sklearn
    job_vector = embedder.encode(job_description).reshape(1, -1)

    # --- THIS IS THE NEW, RELIABLE HYBRID LOGIC ---
    
    # Step 1: Hard Filtering.
    # Use a standard, reliable MongoDB 'find' query to get all candidates that match the skills.
    print(f"Step 1: Applying hard filter to database: {filters}")
    filtered_candidates = list(resumes_collection.find(filters))
    
    if not filtered_candidates:
        print("Database query for skills returned no candidates.")
        return []
        
    print(f"Found {len(filtered_candidates)} candidate(s) that match the skill filter.")

    # Step 2: Semantic Scoring in Python.
    # Now, we loop through the candidates that passed the filter and score them.
    print("Step 2: Calculating semantic similarity for filtered candidates...")
    scored_candidates = []
    for candidate in filtered_candidates:
        if "average_embedding" in candidate and candidate["average_embedding"]:
            # Reshape the candidate's vector for sklearn
            candidate_vector = np.array(candidate["average_embedding"]).reshape(1, -1)
            
            # Calculate the cosine similarity score
            score = cosine_similarity(job_vector, candidate_vector)[0][0]
            
            scored_candidates.append({
                "candidate_info": candidate,
                "search_score": score
            })

    # Step 3: Sort the results by the semantic score.
    sorted_matches = sorted(scored_candidates, key=lambda x: x['search_score'], reverse=True)

    # Step 4: Format the final output.
    final_results = []
    for match in sorted_matches[:limit]:
        final_results.append({
            "_id": match['candidate_info']['_id'],
            "metadata": match['candidate_info']['metadata'],
            "search_score": match['search_score']
        })

    return final_results