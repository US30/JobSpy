# In test_run.py

import pandas as pd
from jobspy import scrape_jobs
from jobspy.database import process_and_store_jobs

# --- Settings ---
pd.set_option('display.max_rows', 20)
pd.set_option('display.max_columns', 10)
pd.set_option('display.width', 1000)

print("🚀 Starting the JobSpy scraper for the TOP 20 GOVERNMENT jobs...")

try:
    # --- Step 1: Scrape only the top 20 jobs ---
    govt_jobs_df = scrape_jobs(
        site_name=["freejobalert"],
        results_wanted=20  # <-- This new parameter will limit the scrape
    )

    if govt_jobs_df is not None and not govt_jobs_df.empty:
        print(f"\n✅ Success! Scraped {len(govt_jobs_df)} government jobs.")
        print("--- Scraped Job Listings (Sample) ---")
        print(govt_jobs_df[['site', 'title', 'company', 'location']].head())
        print("--------------------------------------")

        # --- Step 2: Clear the collection, then store the 20 new jobs ---
        process_and_store_jobs(
            govt_jobs_df, 
            collection_name="govt_jobs",
            clear_collection=True  # <-- This new parameter will auto-delete old data
        )

    else:
        print("\n⚠️ No government jobs were found during scraping.")

except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    import traceback
    traceback.print_exc()