import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime

# Import the correct Job model
from ..model import JobPost, JobResponse, ScraperInput, Location

class FreeJobAlertScraper:
    """
    Scrapes job listings from FreeJobAlert.com, handling data conversion for JobSpy.
    """
    def __init__(self, proxies: Optional[list[str]] = None, ca_cert: Optional[str] = None, user_agent: Optional[str] = None):
        self.site_url = "https://www.freejobalert.com/latest-notifications/"
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.proxies = {'http': proxies, 'https': proxies} if proxies else None
        self.verify = ca_cert or True

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        try:
            response = requests.get(self.site_url, headers=self.headers, proxies=self.proxies, verify=self.verify)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return JobResponse(jobs=[])

        soup = BeautifulSoup(response.content, 'html.parser')
        content_container = soup.find('div', id='content')
        if not content_container:
            return JobResponse(jobs=[])

        all_job_tables = content_container.find_all('table')
        if not all_job_tables:
            return JobResponse(jobs=[])

        job_list: List[JobPost] = []
        for table in all_job_tables:
            category_tag = table.find_previous('strong')
            category = category_tag.text.strip() if category_tag else 'Uncategorized'
            
            job_rows = table.find_all('tr', class_='lattrbord latoclr')
            for row in job_rows:
                cells = row.find_all('td')
                if len(cells) == 7:
                    date_posted_str = cells[0].text.strip()
                    expiry_date_str = cells[5].text.strip()
                    try:
                        posted_date_obj = datetime.strptime(date_posted_str, '%d/%m/%Y')
                    except (ValueError, TypeError):
                        posted_date_obj = None
                    try:
                        expiry_date_obj = datetime.strptime(expiry_date_str, '%d/%m/%Y')
                    except (ValueError, TypeError):
                        expiry_date_obj = None

                    qualification_text = cells[3].text.strip()
                    full_description = f"Category: {category}\n\nQualification: {qualification_text}"

                    # --- THE FIX IS ON THIS LINE ---
                    # Provide an empty string '' instead of None if the link is not found
                    details_link = cells[6].find('a')['href'] if cells[6].find('a') else ''
                    
                    job = JobPost(
                        title=cells[2].text.strip(),
                        company_name=cells[1].text.strip(),
                        location=None,
                        job_url=details_link, # This will now always be a string
                        description=full_description,
                        date_posted=posted_date_obj,
                        job_type=None,
                        expiry_date=expiry_date_obj
                    )
                    job_list.append(job)

        return JobResponse(jobs=job_list)