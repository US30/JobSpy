# In test_run.py

from jobspy import scrape_jobs
from jobspy.database import process_and_store_jobs

# This script will find and store a Python/Java job
jobs_df = scrape_jobs(
    site_name=["linkedin"],
    search_term="Python Software Engineer", # <-- Search for a Python job
    location="New York, NY",
    results_wanted=5,
    linkedin_fetch_description=True
)

if jobs_df is not None and not jobs_df.empty:
    # Store the new jobs in the 'private_jobs' collection
    process_and_store_jobs(jobs_df, collection_name="private_jobs")
    print("\nSuccessfully scraped and stored new Python jobs.")