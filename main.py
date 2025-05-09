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

def build_search_url(keywords, location):
    # Prepare keyword portion
    if isinstance(keywords, list):
        keyword_query = "%20OR%20".join([kw.replace(" ", "%20") for kw in keywords])
    else:
        keyword_query = keywords.replace(" ", "%20")

    # Encode location
    location_query = location.replace(" ", "%20").replace(",", "%2C")

    # Filter parameters
    filters = {
        "keywords": keyword_query,
        "location": location_query,
        "f_TPR": "r604800",  # Filter for jobs posted in the last 7 days
        # Optionally, add more filters here if desired:
        # "f_WT": "2",       # Full-time jobs
        # "f_E": "2,3",      # Entry & Associate levels
        "position": "1",
        "pageNum": "0"
    }

    # Construct full URL
    query_string = "&".join(f"{key}={value}" for key, value in filters.items())
    return f"https://www.linkedin.com/jobs/search/?{query_string}"


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
def scrape_jobs(driver, test_mode=False, keyword=None, location=None, debug=False):
    print("🔍 Starting job scrape...")
    jobs = []

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.randint(5, 10))

    try:
        job_cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "job-card-container"))
        )
        print(f"📦 Found {len(job_cards)} job cards")
    except Exception as e:
        print(f"⚠️ Error while waiting for job cards: {e}")
        return []

    if test_mode:
        print("🧪 Test mode active: limiting to first 3 job cards")
        job_cards = job_cards[:3]

    for idx, card in enumerate(job_cards, 1):
        if debug:
            print(f"\n🧩 Job card HTML snippet #{idx}:")
            print(card.get_attribute('outerHTML'))

        # try:
        #     text = card.text.lower()
        #     if "promoted" in text:
        #         print(f"🚫 Skipping promoted job #{idx}")
        #         continue

        try:
            title_element = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title--link")
            title = title_element.find_element(By.TAG_NAME, "strong").text
        except Exception:
            title = "No title"
            if debug:
                print(f"⚠️ Could not extract title for job #{idx}")

        # Filter out internship titles
        if "intern" in title.lower():
            print(f"🚫 Skipping internship job card #{idx}")
            continue

        try:
            company = card.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle").text
        except Exception:
            company = "No company info"
            if debug:
                print(f"⚠️ Could not extract company for job #{idx}")

        try:
            locations = card.find_elements(By.CSS_SELECTOR, "ul.job-card-container__metadata-wrapper li span")
            job_location = ", ".join([loc.text.strip() for loc in locations])
        except Exception:
            job_location = "No location info"
            if debug:
                print(f"⚠️ Could not extract location for job #{idx}")

        try:
            metadata_items = card.find_elements(By.CSS_SELECTOR, "ul.job-card-container__metadata-wrapper li")
            status = ", ".join(
                [item.text.strip() for item in metadata_items if "Remote" in item.text or "Hybrid" in item.text])
            if not status:
                status = "No status info"
        except Exception:
            status = "No status info"
            if debug:
                print(f"⚠️ Could not extract status for job #{idx}")

        try:
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
        except Exception:
            link = "No link"
            if debug:
                print(f"⚠️ Could not extract link for job #{idx}")

        jobs.append({
            "title": title,
            "company": company,
            "location": job_location,
            "status": status,
            "link": link,
            "search_keyword": keyword,
            "search_location": location
        })

        # Randomized wait after scraping each job card
        time.sleep(random.randint(5, 10))   # Randomized wait time of 5-10 seconds.

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
    # You can set test_mode directly to True or False
    test_mode = False  # Change this to True to limit to first 3 jobs for testing

    if not can_make_request():
        print("❌ Weekly Requests have been reached")
        exit()

    # Start the driver and log in to LinkedIn
    driver = create_driver()
    login(driver)

    # Define the search keywords and locations
    search_keywords = ["Software Engineer", "Software Developer"]
    locations = [
        "Houston, Texas, United States",
        "Austin, Texas, United States",
        "Remote",
        "New York, United States",
        "Seattle, Washington"
    ]

    all_jobs = []

    # Loop through keyword-location pairs and scrape job listings
    for keyword in search_keywords:
        for location in locations:
            print(f"\n🌍 Searching for '{keyword}' jobs in {location}")
            url = build_search_url(keyword, location)  # Pass keyword as a string
            driver.get(url)
            time.sleep(5)

            # Pass test_mode, keyword, and location to scrape_jobs
            jobs = scrape_jobs(driver, test_mode=test_mode, keyword=keyword, location=location)
            all_jobs.extend(jobs)

    # Save the collected jobs to CSV
    save_to_csv(all_jobs)

    # Record the request to avoid hitting limits
    record_request()

    # Quit the driver after finishing
    driver.quit()

