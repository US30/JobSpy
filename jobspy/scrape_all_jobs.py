# Import necessary libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
from tabulate import tabulate


def scrape_all_freejobalert():
    """
    Scrapes ALL job categories from the freejobalert latest notifications page,
    categorizes them, and prints them in a single, unified table.
    """
    URL = "https://www.freejobalert.com/latest-notifications/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print("Fetching job data from the website...")
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch the webpage. {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the main container where all the job tables reside
    content_container = soup.find('div', id='content')
    
    if not content_container:
        print("Error: Could not find the main content container (div with id='content').")
        return

    # --- KEY CHANGE: Find ALL tables within the container ---
    all_job_tables = content_container.find_all('table')
    
    if not all_job_tables:
        print("Error: No job tables were found on the page.")
        return

    print(f"Found {len(all_job_tables)} job tables (categories). Processing all...")
    
    # This list will store jobs from ALL categories
    all_scraped_jobs = []

    # Loop through each table we found
    for table in all_job_tables:
        # Try to find the heading for the current table. 
        # The headings are in <strong> tags right before each table.
        # find_previous('strong') is a good way to get the category title.
        category_tag = table.find_previous('strong')
        category = category_tag.text.strip() if category_tag else 'Uncategorized'

        # Find all job rows within the CURRENT table
        job_rows = table.find_all('tr', class_='lattrbord latoclr')
        
        # Process each row in this table
        for row in job_rows:
            cells = row.find_all('td')
            
            if len(cells) == 7:
                date_posted = cells[0].text.strip()
                company = cells[1].text.strip()
                job_title_posts = cells[2].text.strip()
                qualification = cells[3].text.strip()
                last_date = cells[5].text.strip()
                
                details_link_tag = cells[6].find('a')
                details_link = details_link_tag['href'] if details_link_tag else 'N/A'
                
                # Create a dictionary for the job, now including its category
                job_data = {
                    "Category": category, # Added category
                    "Date Posted": date_posted,
                    "Company": company,
                    "Post Name & Vacancies": job_title_posts,
                    "Qualification": qualification,
                    "Last Date": last_date,
                    "Details Link": details_link
                }
                all_scraped_jobs.append(job_data)

    if not all_scraped_jobs:
        print("No job data was extracted. Check the website for changes.")
        return

    # Create a single DataFrame from the comprehensive list of all jobs
    df = pd.DataFrame(all_scraped_jobs)
    
    # Set display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    print("\n--- All Latest Government Job Notifications ---")
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
    print(f"\n--- Scraping Complete: Found a total of {len(all_scraped_jobs)} jobs. ---")

# Run the main function
if __name__ == "__main__":
    scrape_all_freejobalert()