import os
import time
import re
import random
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import process_html_files, json_to_reviews_dataframe, analyze_sentiment_and_extract_words

# Constants
HTML_FILES_FOLDER = 'html_files'
OUTPUT_JSON_FILE = 'product_data.json'
SELENIUM_WAIT_TIME = 20
RANDOM_DELAY_MIN = 3
RANDOM_DELAY_MAX = 10
AMAZON_LOGIN_URL = "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

def extract_asin_from_url(url):
    asin_pattern = r'/([A-Z0-9]{10})(?:[/?]|$)'
    match = re.search(asin_pattern, url)
    return match.group(1) if match else None

def construct_paginated_url_from_url(url, page_number):
    product_id = extract_asin_from_url(url)
    if product_id:
        base_url = f"https://www.amazon.com/product-reviews/{product_id}/ref=cm_cr_arp_d_paging_btm_next_2"
        return f"{base_url}?pageNumber={page_number}"
    else:
        raise ValueError("Could not extract product ID (ASIN) from URL.")

def save_page_content(driver, file_number, folder_path):
    page_source = driver.page_source
    file_path = os.path.join(folder_path, f'amazon_reviews_page_{file_number}.html')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(page_source)
    logger.info(f"Page saved successfully as '{file_path}'")

def initialize_webdriver():
    try:
        return webdriver.Chrome()  # Change to webdriver.Firefox() if using Firefox
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        raise

def login_amazon(driver, email, password):
    try:
        driver.get(AMAZON_LOGIN_URL)
        WebDriverWait(driver, SELENIUM_WAIT_TIME).until(
            EC.presence_of_element_located((By.ID, "ap_email"))
        )
        driver.find_element(By.ID, "ap_email").send_keys(email)
        time.sleep(random.randint(3, 5))  # Random delay between 3 to 5 seconds
        driver.find_element(By.ID, "continue").click()

        WebDriverWait(driver, SELENIUM_WAIT_TIME).until(
            EC.presence_of_element_located((By.ID, "ap_password"))
        )
        time.sleep(random.randint(3, 5))  # Random delay between 3 to 5 seconds
        driver.find_element(By.ID, "ap_password").send_keys(password)
        time.sleep(random.randint(3, 5))  # Random delay between 3 to 5 seconds
        driver.find_element(By.ID, "signInSubmit").click()

        WebDriverWait(driver, SELENIUM_WAIT_TIME).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        logger.info("Logged in to Amazon successfully.")
    except Exception as e:
        logger.error(f"Error during Amazon login: {e}")
        raise

def click_next_page_button(driver):
    try:
        next_page_button = WebDriverWait(driver, SELENIUM_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, "//li[@class='a-last']/a"))
        )
        delay = random.randint(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
        logger.info(f"Waiting for {delay} seconds before clicking 'Next page' button.")
        time.sleep(delay)
        next_page_button.click()
        logger.info("Clicked 'Next page' button.")
        time.sleep(5)  # Wait for the new page to load
    except Exception as e:
        logger.info("No more 'Next page' button found or not clickable:", str(e))
        return False
    return True

@csrf_exempt
def scrape_amazon_reviews(request):
    if request.method == 'POST':
        amazon_url = request.POST.get('amazon_url')
        amazon_email = 'ghayurabbas13@gmail.com'
        amazon_password = '12345678@abc'
        try:
            if not os.path.exists(HTML_FILES_FOLDER):
                os.makedirs(HTML_FILES_FOLDER)

            driver = initialize_webdriver()
            login_amazon(driver, amazon_email, amazon_password)

            page_number = 1
            while True:
                paginated_url = construct_paginated_url_from_url(amazon_url, page_number)
                logger.info(f"Opening URL: {paginated_url}")
                driver.get(paginated_url)
                WebDriverWait(driver, SELENIUM_WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                save_page_content(driver, page_number, HTML_FILES_FOLDER)
                page_number += 1
                if not click_next_page_button(driver):
                    break

            driver.quit()
            return JsonResponse({'message': 'Scraping completed successfully.'})
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

@csrf_exempt
def perform_sentiment_analysis(request):
    if request.method == 'GET':
        try:
            process_html_files(HTML_FILES_FOLDER, OUTPUT_JSON_FILE)
            reviews_df = json_to_reviews_dataframe(OUTPUT_JSON_FILE)
            positive_percent, negative_percent, neutral_percent, positive_words_str, negative_words_str, neutral_words_str = analyze_sentiment_and_extract_words(reviews_df)

            data = {
                'positive_percent': positive_percent,
                'negative_percent': negative_percent,
                'neutral_percent': neutral_percent,
                'positive_words': positive_words_str,
                'negative_words': negative_words_str,
                'neutral_words': neutral_words_str
            }
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request.'}, status=400)
