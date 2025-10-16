# In jobspy/analysis/matching.py

import os
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .llm_analyser import extract_skills_with_llm

# --- Initialize components for this module ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_CONNECTION_STRING)
db = client["job_database"]
resumes_collection = db["resumes"]
jobs_collection = db["private_jobs"] # Or "govt_jobs"

print("Initializing sentence-transformer model for matching...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("Matching model initialized.")

def get_average_embedding(chunks: list) -> np.ndarray:
    """ Averages the embedding vectors from a list of chunks. """
    if not chunks:
        return np.zeros(embedder.get_sentence_embedding_dimension())
    
    embeddings = [chunk['embedding'] for chunk in chunks]
    return np.mean(embeddings, axis=0)

def calculate_skill_overlap(job_skills: list, resume_skills: list) -> float:
    """ Calculates a skill overlap score (Jaccard similarity). """
    if not job_skills or not resume_skills:
        return 0.0
    
    set_job = set(s.lower() for s in job_skills)
    set_resume = set(s.lower() for s in resume_skills)
    
    intersection = len(set_job.intersection(set_resume))
    union = len(set_job.union(set_resume))
    
    return intersection / union if union != 0 else 0.0

def find_best_resumes_for_job(job_id: str, limit: int = 5):
    """
    Finds the best matching resumes for a job by calculating a combined
    semantic similarity and skill overlap score.
    """
    # 1. Fetch the job and extract its skills and average embedding
    job = jobs_collection.find_one({"_id": job_id})
    if not job:
        print(f"Job with ID '{job_id}' not found.")
        return []
    
    print(f"\n--- Matching against Job: {job['metadata']['title']} at {job['metadata']['company']} ---")
    
    job_skills = extract_skills_with_llm(job.get('full_description_raw', ''))
    job_embedding = get_average_embedding(job.get('chunks', []))
    print(f"Job skills: {job_skills}")

    # 2. Fetch all resumes
    all_resumes = list(resumes_collection.find({}))
    if not all_resumes:
        print("No resumes found in the database to compare against.")
        return []

    # 3. Calculate scores for each resume
    match_scores = []
    for resume in all_resumes:
        resume_embedding = get_average_embedding(resume.get('chunks', []))
        resume_skills = resume.get('metadata', {}).get('extracted_skills', [])
        
        # Calculate semantic similarity (cosine similarity)
        semantic_score = cosine_similarity([job_embedding], [resume_embedding])[0][0]
        
        # Calculate skill overlap score
        skill_score = calculate_skill_overlap(job_skills, resume_skills)
        
        # Combine scores (e.g., 70% semantic, 30% skill overlap)
        final_score = (0.7 * semantic_score) + (0.3 * skill_score)
        
        match_scores.append({
            "candidate_name": resume['metadata']['name'],
            "candidate_id": resume['_id'],
            "final_score": final_score,
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "matching_skills": list(set(s.lower() for s in job_skills).intersection(set(s.lower() for s in resume_skills)))
        })
        
    # 4. Sort resumes by the final score in descending order
    sorted_matches = sorted(match_scores, key=lambda x: x['final_score'], reverse=True)
    
    return sorted_matches[:limit]