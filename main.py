# main.py

import json
import os
import time
import random
from datetime import datetime, timedelta
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
from dotenv import load_dotenv


# CONFIG
load_dotenv()
REQUEST_LOG= "request_count.json"
JOBS_CSV = "data/linkedin_jobs.csv"
MAX_WEEKLY_REQUESTS = 25    # 25 so we don't get banned lol
SEARCH_URL = "https://www.linkedin.com/jobs/software-engineer-jobs-houston-tx/?currentJobId=4224572050"
USERNAME = os.getenv("LINKEDIN_USERNAME")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# --- Request Limitations ----
def load_request_log():
    if os.path.exists(REQUEST_LOG):
        with open(REQUEST_LOG, "r") as f:
            return json.load(f)
    return []

def save_request_log(log):
    with open(REQUEST_LOG, "w") as f:
        json.dump(log, f)

def can_make_request():
    log = load_request_log()

    one_week_ago = datetime.now() - timedelta(days=7)
    recent_requests = [t for t in log if datetime.fromisoformat(t) > one_week_ago]

    if len(recent_requests) >= MAX_WEEKLY_REQUESTS:
        print("Weekly Requests have been reached.")
        return False
    return True

def record_request():
    log = load_request_log()
    log.append(datetime.now().isoformat())
    save_request_log(log)

# Selenium Setup
def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)


# Linkedin Login Setup
def login(driver):
    print("Logging on into Linkedin..")
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)

    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)

# Go to Job Searching Page
def go_to_job_search(driver):
    print(f"Navigating Job Search page: {SEARCH_URL}")
    driver.get(SEARCH_URL)
    time.sleep(5)

# Scraping Jobs
def scrape_jobs(driver, test_mode=False):
    print("🔍 Starting job scrape...")
    jobs = []

    # Scroll once to ensure job cards are visible
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    try:
        job_cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container"))
        )
        print(f"Found {len(job_cards)} job cards")
    except Exception as e:
        print(f"⚠️ Error while waiting for job cards: {e}")
        return []

    if test_mode:
        print("🧪 Test mode active: limiting to first 3 job cards")
        job_cards = job_cards[:3]

    for idx, card in enumerate(job_cards, 1):
        try:
            # Skip promoted jobs
            text = card.text.lower()
            if "promoted" in text:
                print(f"🚫 Skipping promoted job card #{idx}")
                continue

            # Extract job details for non-promoted cards
            try:
                title_element = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title--link")
                title = title_element.find_element(By.TAG_NAME, "strong").text  # Extract the strong text
            except Exception as e:
                title = "No title"
                print(f"⚠️ Error extracting title for job card #{idx}: {e}")

            try:
                company = card.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle").text
            except Exception as e:
                company = "No company info"
                print(f"⚠️ Error extracting company for job card #{idx}: {e}")

            try:
                location = card.find_element(By.CSS_SELECTOR, "ul.job-card-container__metadata-wrapper li").text
            except Exception as e:
                location = "No location info"
                print(f"⚠️ Error extracting location for job card #{idx}: {e}")

            try:
                link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            except Exception as e:
                link = "No link"
                print(f"⚠️ Error extracting link for job card #{idx}: {e}")

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "link": link
            })

        except Exception as e:
            print(f"⚠️ Unexpected Exception for job card #{idx}: {e}")

    print(f"✅ Scraped {len(jobs)} non-promoted job(s)")
    return jobs


# -- Saving to CSV --
def save_to_csv(jobs):
    if not os.path.exists("data"):
        os.makedirs("data")
    df = pd.DataFrame(jobs)
    df.to_csv(JOBS_CSV, index=False)
    print(f"Saved Jobs to {JOBS_CSV}")

# Main Execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument('--test', action='store_true', help='Run in test mode (2 - 3 Listings only')
    args = parser.parse_args()

    if not can_make_request():
        print("Weekly Requests have been reached")
        exit()

    driver = create_driver()
    login(driver)
    url = "https://www.linkedin.com/jobs/search/?keywords=Software%20Engineer&location=Houston%2C%20Texas%2C%20United%20States"
    driver.get(url)
    time.sleep(5)

    jobs = scrape_jobs(driver, test_mode=args.test)
    save_to_csv(jobs)
    record_request()
    driver.quit()
