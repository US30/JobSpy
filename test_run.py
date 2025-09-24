# In test_run.py

import pandas as pd
from jobspy import scrape_jobs

# --- Settings to make the output readable in the terminal ---
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', 70) # Increased width for long URLs

print("🚀 Starting the JobSpy scraper...")

try:
    jobs_df = scrape_jobs(site_name=["freejobalert"])

    if jobs_df is not None and not jobs_df.empty:
        print(f"\n✅ Success! Scraped {len(jobs_df)} jobs from FreeJobAlert.")
        print("--- Job Listings ---")
        
        # --- THE FIX IS ON THIS LINE ---
        # The final DataFrame uses 'company', not 'company_name'.
        print(jobs_df[['site', 'title', 'company', 'job_url', 'date_posted']])
        
        print("--------------------")
    else:
        print("\n⚠️ No jobs were found. The scraper ran successfully but returned no data.")

except Exception as e:
    print(f"\n❌ An error occurred during the final display: {e}")