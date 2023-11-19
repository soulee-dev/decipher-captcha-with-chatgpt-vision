import logging
import sqlite3
import base64
import time
import random
from contextlib import contextmanager
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
from dotenv import load_dotenv

load_dotenv()
CAPTCHA_URL = os.getenv('CAPTCHA_URL')
DATABASE_NAME = os.getenv('DATABASE_NAME')
NID_AUT = os.getenv("NID_AUT")
NID_SES = os.getenv("NID_SES")
FETCH_COUNT = 500
TIMEOUT = 10

logging.basicConfig(level=logging.INFO)


@contextmanager
def create_webdriver():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def set_cookies(driver):
    driver.get("https://shopping.naver.com")

    driver.add_cookie(
        {
            "name": "NID_AUT",
            "value": os.getenv("NID_AUT"),
            "domain": ".naver.com",
            "path": "/",
        }
    )
    driver.add_cookie(
        {
            "name": "NID_SES",
            "value": os.getenv("NID_SES"),
            "domain": ".naver.com",
            "path": "/",
        }
    )

def fetch_captcha_image(driver):
    try:
        element = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "captchaimg"))
        )
        return element.get_attribute("src").split(",")[1], driver.find_element(By.ID, "captcha_info").text
    except TimeoutException:
        logging.error("Loading took too much time!")

def initialize_database():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captchas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image BLOB NOT NULL,
                question TEXT NOT NULL,
                answer TEXT
            )
        ''')

def save_img(conn, img_base64, question):
    img_bytes = base64.b64decode(img_base64)
    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO captchas (image, question) VALUES (?, ?)''', (img_bytes, question))
        conn.commit()
    except sqlite3.Error as error:
        print("Failed to insert data into sqlite table", error)

def main():
    initialize_database()
    with create_webdriver() as driver, sqlite3.connect(DATABASE_NAME) as conn:
        set_cookies(driver)
        driver.get(CAPTCHA_URL)
        for _ in tqdm(range(FETCH_COUNT), desc="Fetching CAPTCHAs"):
            try:
                img_base64, question = fetch_captcha_image(driver)
                save_img(conn, img_base64, question)
                time.sleep(random.uniform(0.5, 1))
                driver.refresh()
            except Exception as e:
                logging.error(f"An error occurred: {e}")

    logging.info("The SQLite connection is closed")

if __name__ == "__main__":
    main()
