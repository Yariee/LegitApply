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

