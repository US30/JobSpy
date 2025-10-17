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
    Performs a true hybrid search using a $search stage with the correct knnBeta
    operator, which includes the filter directly inside it.
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
    
    # 1. Start by defining the core knnBeta operator
    knn_beta_operator = {
        "vector": query_vector,
        "path": "average_embedding",
        # k is the number of nearest neighbors to find *after* the filter is applied.
        "k": 50 
    }

    # 2. Add the filter directly inside the knnBeta operator if it exists
    if filters and "metadata.extracted_skills" in filters and "$in" in filters["metadata.extracted_skills"]:
        print(f"Applying pre-filter: {filters}")
        skills_to_find = filters["metadata.extracted_skills"]["$in"]
        
        knn_beta_operator["filter"] = {
            "in": {
                "path": "metadata.extracted_skills",
                "value": skills_to_find
            }
        }
    
    # 3. Construct the final, correct aggregation pipeline
    pipeline = [
        {
            "$search": {
                "index": "vector_index",
                "knnBeta": knn_beta_operator
            }
        },
        {
            "$project": {
                "_id": 1,
                "metadata": 1,
                "search_score": { "$meta": "searchScore" }
            }
        },
        {
            "$limit": limit
        }
    ]

    # 4. Execute the search
    try:
        print("Executing definitive hybrid search pipeline...")
        results = list(resumes_collection.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Hybrid search failed. Error: {e}")
        return []