# In jobspy/analysis/matching.py

import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

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
    Performs a reliable, two-step hybrid search using post-filtering.
    Step 1: Broad semantic vector search.
    Step 2: Precise metadata filtering on the semantic results.
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
    
    query_vector = embedder.encode(job_description).tolist()

    # --- THIS IS THE DEFINITIVE HYBRID SEARCH PIPELINE ---

    # Step 1: Perform a broad SEMANTIC search using $vectorSearch.
    # This gets the top N most similar candidates, regardless of skills.
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "average_embedding",
                "queryVector": query_vector,
                "numCandidates": 200, # Cast a wide net
                "limit": 100          # Get the top 100 semantic matches
            }
        },
        {
            # Project the IDs and the search score so we can filter in the next step
            "$project": {
                "_id": 1,
                "search_score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    try:
        print("Step 1: Executing broad semantic search...")
        semantic_results = list(resumes_collection.aggregate(pipeline))
        if not semantic_results:
            print("Semantic search returned no initial candidates.")
            return []
        
        print(f"Found {len(semantic_results)} semantically similar candidates.")
        
        # Create a dictionary to hold the scores for easy lookup
        candidate_scores = {result['_id']: result['search_score'] for result in semantic_results}
        candidate_ids = list(candidate_scores.keys())

        # Step 2: Perform a precise METADATA filter on the results of Step 1.
        print(f"Step 2: Applying hard filter to the {len(candidate_ids)} candidates: {filters}")
        
        # Build the final query
        final_query = {
            "_id": { "$in": candidate_ids } # Only search within the semantic results
        }
        # Add the skill filters to the query
        final_query.update(filters)
        
        # Execute the final find query
        hybrid_matches = list(resumes_collection.find(final_query))
        
        # Add the search score back to the final results
        for match in hybrid_matches:
            match['search_score'] = candidate_scores.get(match['_id'])
            
        # Sort the final list by the semantic score
        sorted_matches = sorted(hybrid_matches, key=lambda x: x['search_score'], reverse=True)

        # Format the output
        final_results = []
        for match in sorted_matches[:limit]:
            final_results.append({
                "_id": match['_id'],
                "metadata": match['metadata'],
                "search_score": match['search_score']
            })

        return final_results

    except Exception as e:
        print(f"Hybrid search failed. Error: {e}")
        return []