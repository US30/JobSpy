# In jobspy/database.py

import os
import re
from datetime import datetime, date, time, timezone
from pymongo import MongoClient
import pandas as pd
from sentence_transformers import SentenceTransformer
import pymongo

# --- CONFIGURATION ---
MONGO_CONNECTION_STRING = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DATABASE_NAME = "job_database"
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

# --- INITIALIZATION ---
print("Initializing sentence-transformer model for embeddings...")
embedder = SentenceTransformer(EMBEDDING_MODEL)
print("Embedding model initialized.")

client = MongoClient(MONGO_CONNECTION_STRING)
db = client[MONGO_DATABASE_NAME]
print(f"Connected to MongoDB. Using database '{MONGO_DATABASE_NAME}'.")

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

def setup_database():
    """ Ensures all necessary collections and their indexes are ready. """
    print("Setting up database collections and indexes...")
    create_indexes("private_jobs")
    create_indexes("govt_jobs")
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
    
    # --- THIS IS THE CORRECTED REGEX LOGIC ---
    # 1. The pattern does NOT have the inline (?i) flag.
    pattern = r'\n\s*(' + '|'.join(re.escape(h) for h in headers) + r')\s*[:\-]*\s*\n'
    
    # 2. The IGNORECASE flag is passed as a separate argument.
    chunks = re.split(pattern, text, flags=re.IGNORECASE)
    # --- END OF FIX ---
    
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


def process_and_store_jobs(jobs_df: pd.DataFrame, collection_name: str, clear_collection: bool = False):
    """
    Processes jobs, generates embeddings, and stores them in a specified MongoDB collection.
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
        chunk_embeddings = embedder.encode(chunks_text).tolist() if chunks_text else []
        chunks_data = [{"chunk_text": text, "embedding": chunk_embeddings[i]} for i, text in enumerate(chunks_text)]

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