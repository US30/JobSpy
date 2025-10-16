# In jobspy/scrapers/freejobalert.py

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime

from ..model import JobPost, JobResponse, ScraperInput, Location

def robust_date_parser(date_str: str) -> Optional[datetime]:
    """
    A helper function that can parse date strings with either slashes or dashes.
    Returns a datetime object or None if parsing fails.
    """
    if not date_str or date_str == '-':
        return None
    # List of possible date formats the site might use
    for fmt in ('%d-%m-%Y', '%d/%m/%Y'): 
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue # If parsing fails, try the next format
    
    print(f"Warning: Could not parse date string '{date_str}' with any known format.")
    return None

class FreeJobAlertScraper:
    """
    Scrapes job listings from FreeJobAlert.com.
    Performs a "deep scrape" of details pages, extracts structured data from tables,
    and skips duplicate companies within a single session.
    """
    def __init__(self, proxies: Optional[list[str]] = None, ca_cert: Optional[str] = None, user_agent: Optional[str] = None):
        self.site_url = "https://www.freejobalert.com/latest-notifications/"
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.proxies = {'http': proxies, 'https': proxies} if proxies else None
        self.verify = ca_cert or True

    def _scrape_details_page(self, url: str) -> Dict[str, str]:
        """
        Helper function to scrape the structured data table from a job's details page.
        Returns a dictionary of the found fields.
        """
        details_data = {}
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies, verify=self.verify, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            post_content = soup.find('div', class_='post')
            if not post_content:
                return details_data

            tables = post_content.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            details_data[key] = value
            
            if not details_data:
                details_data['Full Text'] = post_content.get_text(separator='\n', strip=True)

            return details_data
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch details page {url}. Error: {e}")
            return details_data

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        try:
            response = requests.get(self.site_url, headers=self.headers, proxies=self.proxies, verify=self.verify)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.content, 'html.parser')
        content_container = soup.find('div', id='content')
        if not content_container: return JobResponse(jobs=[])
        all_job_tables = content_container.find_all('table')
        if not all_job_tables: return JobResponse(jobs=[])

        job_list: List[JobPost] = []
        results_wanted = scraper_input.results_wanted
        processed_companies = set()

        for table in all_job_tables:
            if len(job_list) >= results_wanted:
                print(f"Reached the desired number of jobs ({results_wanted}). Stopping scrape.")
                break
            
            category_tag = table.find_previous('strong')
            category = category_tag.text.strip() if category_tag else 'Uncategorized'
            
            job_rows = table.find_all('tr', class_='lattrbord latoclr')
            for row in job_rows:
                if len(job_list) >= results_wanted:
                    break
                
                cells = row.find_all('td')
                if len(cells) == 7:
                    recruitment_board = cells[1].text.strip()
                    if recruitment_board in processed_companies:
                        print(f"Skipping duplicate company: {recruitment_board}")
                        continue
                    
                    date_posted_str = cells[0].text.strip()
                    post_name = cells[2].text.strip()
                    qualification_summary = cells[3].text.strip()
                    advt_no = cells[4].text.strip()
                    expiry_date_str = cells[5].text.strip()
                    details_link = cells[6].find('a')['href'] if cells[6].find('a') else ''

                    details_data = {}
                    if details_link:
                        print(f"Fetching details for job #{len(job_list) + 1}: {post_name} at {recruitment_board}")
                        details_data = self._scrape_details_page(details_link)
                    
                    details_text_parts = []
                    for key, value in details_data.items():
                        details_text_parts.append(f"{key}: {value}")
                    details_text = "\n".join(details_text_parts)

                    combined_description = (
                        f"Category: {category}\n"
                        f"Qualification Summary: {qualification_summary}\n"
                        f"Advertisement No.: {advt_no if advt_no and advt_no != '-' else 'N/A'}\n\n"
                        f"--- Full Job Details ---\n"
                        f"{details_text}"
                    )
                    
                    # Use the new robust parser for both dates
                    start_date_str = details_data.get('Start Date for Apply Online', date_posted_str)
                    last_date_str = details_data.get('Last Date for Apply Online', expiry_date_str)

                    posted_date_obj = robust_date_parser(start_date_str)
                    expiry_date_obj = robust_date_parser(last_date_str)

                    job = JobPost(
                        title=post_name,
                        company_name=recruitment_board,
                        location=None,
                        job_url=details_link,
                        description=combined_description.strip(),
                        date_posted=posted_date_obj,
                        job_type=None,
                        expiry_date=expiry_date_obj
                    )
                    job_list.append(job)
                    processed_companies.add(recruitment_board)

        return JobResponse(jobs=job_list)