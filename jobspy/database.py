import os
import re
import numpy as np
from datetime import datetime, date, time, timezone
from pymongo import MongoClient
import pandas as pd
import openai
import pymongo
from typing import List, Dict, Optional 

# --- New Imports ---
from .analysis.resume_parser import parse_resume
from .analysis.llm_analyser import extract_skills_with_llm

# --- CONFIGURATION ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_URI")
if not MONGO_CONNECTION_STRING:
    raise ValueError("MONGO_URI environment variable not set. Please create a .env file.")
MONGO_DATABASE_NAME = "job_database"
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")

# --- INITIALIZATION ---
if "AZURE_OPENAI_ENDPOINT" not in os.environ or "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError("AZURE_OPENAI_ENDPOINT and OPENAI_API_KEY environment variables not found.")

client = openai.AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["OPENAI_API_KEY"],
    api_version=os.environ.get("OPENAI_API_VERSION", "2025-04-01-preview")
)
print("Azure OpenAI client initialized.")

if "AZURE_OPENAI_EMBEDDING_ENDPOINT" not in os.environ or "OPENAI_EMBEDDING_API_KEY" not in os.environ:
    raise EnvironmentError("AZURE_OPENAI_EMBEDDING_ENDPOINT and OPENAI_EMBEDDING_API_KEY environment variables not found.")

embedding_client = openai.AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_EMBEDDING_ENDPOINT"],
    api_key=os.environ["OPENAI_EMBEDDING_API_KEY"],
    api_version=os.environ.get("OPENAI_EMBEDDING_API_VERSION", "2023-05-15")
)
print("Azure OpenAI embedding client initialized.")

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client[MONGO_DATABASE_NAME]
print(f"Connected to MongoDB. Using database '{MONGO_DATABASE_NAME}'.")

def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> Optional[list[float]]:
    """Generates an embedding for a given text using Azure OpenAI's API."""
    if not text:
        return None
    try:
        response = embedding_client.embeddings.create(input=[text], model=model, dimensions=384)
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def create_indexes(collection_name: str):
    """ Creates indexes on a specified collection. """
    print(f"Ensuring indexes exist on '{collection_name}' collection...")
    try:
        collection = db[collection_name]
        collection.create_index([("metadata.company", pymongo.ASCENDING)])
        collection.create_index([("metadata.location", pymongo.ASCENDING)])
        collection.create_index([("metadata.date_posted", pymongo.DESCENDING)])
        print(f"Indexes are in place for '{collection_name}'.")
    except Exception as e:
        print(f"An error occurred during index creation for '{collection_name}': {e}")

def create_resume_indexes(collection_name: str):
    """ Creates indexes on the resumes collection for efficient filtering. """
    print(f"Ensuring indexes exist on '{collection_name}' collection...")
    try:
        collection = db[collection_name]
        collection.create_index([("metadata.name", pymongo.ASCENDING)])
        collection.create_index([("metadata.extracted_skills", pymongo.ASCENDING)])
        print(f"Indexes are in place for '{collection_name}'.")
    except Exception as e:
        print(f"An error occurred during resume index creation: {e}")

def setup_database():
    """ Ensures all necessary collections and their indexes are ready. """
    print("Setting up database collections and indexes...")
    create_indexes("private_jobs")
    create_indexes("govt_jobs")
    create_resume_indexes("resumes")
    print("Database setup complete.")

setup_database()

def custom_semantic_chunker(text: str) -> list[str]:
    """ A rule-based chunker that splits job descriptions by common section headers. """
    if not text:
        return []
    headers = [
        "responsibilities", "requirements", "qualifications", "duties",
        "experience", "skills", "about the role", "about you", "your role",
        "what you'll do", "what you will do", "what you'll need", "nice to have", "preferred qualifications"
    ]
    
    pattern = r'\n\s*(' + '|'.join(re.escape(h) for h in headers) + r')\s*[:\-]*\s*\n'
    chunks = re.split(pattern, text, flags=re.IGNORECASE)
    
    reconstructed_chunks = []
    current_chunk_content = [chunks[0].strip()]
    for i in range(1, len(chunks), 2):
        header = chunks[i]
        text_after = chunks[i+1]
        if current_chunk_content[0]:
            reconstructed_chunks.append(current_chunk_content[0])
        current_chunk_content = [(header + ":\n" + text_after).strip()]
    if current_chunk_content[0]:
        reconstructed_chunks.append(current_chunk_content[0])
    if len(reconstructed_chunks) <= 1 and text:
         reconstructed_chunks = [p.strip() for p in text.split('\n\n') if p.strip()]
    return [chunk for chunk in reconstructed_chunks if chunk]

def get_average_embedding(chunks: list) -> Optional[list[float]]:
    """ Averages the embedding vectors from a list of chunks. """
    if not chunks:
        return None
    
    embeddings = [chunk['embedding'] for chunk in chunks if 'embedding' in chunk and chunk['embedding'] is not None]
    if not embeddings:
        return None
        
    avg_embedding = np.mean(embeddings, axis=0)
    return avg_embedding.tolist()

def process_and_store_resume(file_path: str, candidate_name: str, candidate_id: str):
    """
    Parses a resume, extracts skills, creates chunks and embeddings using Azure OpenAI,
    and stores it in the 'resumes' collection.
    """
    print(f"Processing resume for: {candidate_name}")
    
    raw_text = parse_resume(file_path)
    if not raw_text:
        print("Failed to parse resume text.")
        return

    print("Extracting skills with Azure OpenAI...")
    skills = extract_skills_with_llm(raw_text)
    print(f"Extracted skills: {skills}")
    
    chunks_text = custom_semantic_chunker(raw_text)
    chunks_data = [
        {"chunk_text": text, "embedding": get_embedding(text)}
        for text in chunks_text
    ]
    
    average_embedding = get_average_embedding(chunks_data)
    
    resume_document = {
        "_id": candidate_id,
        "processed_timestamp": datetime.now(timezone.utc),
        "metadata": {
            "name": candidate_name,
            "source_file": file_path,
            "extracted_skills": skills
        },
        "full_text_raw": raw_text,
        "chunks": chunks_data,
        "average_embedding": average_embedding
    }

    collection = db["resumes"]
    try:
        collection.update_one({'_id': resume_document['_id']}, {'$set': resume_document}, upsert=True)
        print(f"Successfully stored resume for '{candidate_name}' with average embedding.")
    except Exception as e:
        print(f"An error occurred storing the resume: {e}")

def process_and_store_jobs(jobs_df: pd.DataFrame, collection_name: str, clear_collection: bool = False):
    """
    Processes jobs, generates embeddings using Azure OpenAI, and stores them in a specified MongoDB collection.
    """
    if jobs_df.empty:
        print(f"Received an empty DataFrame. No jobs to process for '{collection_name}'.")
        return

    collection = db[collection_name]

    if clear_collection:
        print(f"Clearing all existing documents from '{collection_name}' collection...")
        try:
            delete_result = collection.delete_many({})
            print(f"Deleted {delete_result.deleted_count} documents.")
        except Exception as e:
            print(f"An error occurred while clearing the collection: {e}")
            return

    print(f"Processing {len(jobs_df)} jobs for '{collection_name}' collection...")
    
    jobs_to_insert = []
    for index, job in jobs_df.iterrows():
        metadata = job.to_dict()
        for date_field in ['date_posted', 'expiry_date']:
            if isinstance(metadata.get(date_field), date) and not isinstance(metadata.get(date_field), datetime):
                metadata[date_field] = datetime.combine(metadata[date_field], time.min)

        full_description = metadata.pop('description', '') or ''
        metadata = {k: (None if pd.isna(v) else v) for k, v in metadata.items()}

        chunks_text = custom_semantic_chunker(full_description)
        chunks_data = [
            {"chunk_text": text, "embedding": get_embedding(text)}
            for text in chunks_text
        ]

        job_id = metadata.get('id') or metadata.get('job_url') or index
        unique_id = f"{metadata.get('site', 'unknown')}_{job_id}"

        job_document = {
            "_id": unique_id,
            "source_site": metadata.get('site'),
            "scraped_timestamp": datetime.now(timezone.utc),
            "metadata": metadata,
            "full_description_raw": full_description,
            "chunks": chunks_data
        }
        
        jobs_to_insert.append(job_document)

    if jobs_to_insert:
        print(f"Inserting {len(jobs_to_insert)} new jobs into '{collection_name}'...")
        try:
            from pymongo import UpdateOne
            bulk_operations = [UpdateOne({'_id': doc['_id']}, {'$set': doc}, upsert=True) for doc in jobs_to_insert]
            result = collection.bulk_write(bulk_operations)
            print(f"MongoDB bulk write summary for '{collection_name}': Matched={result.matched_count}, Modified={result.modified_count}, Upserted={result.upserted_count}")
        except Exception as e:
            print(f"An error occurred during MongoDB bulk insert for '{collection_name}': {e}")
            import traceback
            traceback.print_exc()