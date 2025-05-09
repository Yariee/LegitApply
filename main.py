# main.py

import json
import os
import time
import random
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd

# CONFIG
REQUEST_LOG= "request_log.json"
JOBS_CSV = "data/linkedin_jobs.csv"
MAX_WEEKLY_REQUESTS = 25    # 25 so we don't get banned lol
SEARCH_URL = "https://www.linkedin.com/jobs/software-engineer-jobs-houston-tx/?currentJobId=4224572050"
USERNAME = "your_email@example.com"
PASSWORD = "your_password"

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
    one_week_ago = datetime.now() - timedelta(weeks = 1)
    recent_requests = [t for t in log if datetime.fromisoformat(t) > one_week_ago]
    return len(recent_requests)

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
    driver.find_element(By.ID, "passoword").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)

# Go to Job Searching Page
def go_to_job_search(driver):
    print(f"Navigating Job Search page: {SEARCH_URL}")
    driver.get(SEARCH_URL)
    time.sleep(5)

# Scraping Jobs
def scrape_jobs(driver):
    print("Scraping Jobs..")
    jobs = []
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(3, 5))

    job_cards = driver.find_elements(By.CLASS_NAME, "job-card-container")
    for card in job_cards:
        try:
            title = card.find_element(By.CLASS_NAME, "job-card-list_title").text
            company = card.find_element(By.CLASS_NAME, "job-card-container_company_name").text
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            promoted = "promoted" in card.text.lower()

            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "promote": promoted
            })
        except Exception as e:
            print("Unexpected Exception of: ", e)

    print(f"Scraped {len(jobs)} jobs")
    return jobs

# -- Saving to CSV --
def save_to_csv(jobs):
    if not os.path.exists("data"):
        os.makedirs("")
    df = pd.DataFrame(jobs)
    df.to_csv(JOBS_CSV, index=False)
    print(f"Saved Jobs to {JOBS_CSV}")

# Main Execution
if __name__ == "__main__":
    if not can_make_request():
        print("Weekly Requests have been reached")
        exit()

    driver = create_driver()
    try:
        record_request()    # Log the request we are making
        login(driver)
        go_to_job_search(driver)
        jobs = scrape_jobs(driver)
        save_to_csv(jobs)
    finally:
        driver.quit()
