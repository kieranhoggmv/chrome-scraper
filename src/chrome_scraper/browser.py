import glob
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from chromedriver_py import binary_path

load_dotenv()


class NotConfiguredException(Exception):
    pass


class _Browser:
    BY = By

    def __init__(self, kill_windows=True, skip_confirmation=False):
        LOCAL_USER = os.getenv("LOCAL_USER")
        if not LOCAL_USER:
            raise NotConfiguredException("LOCAL_USER needs to defined in .env")
        CHROME_PROFILE = os.getenv("CHROME_PROFILE", default=None)
        PROFILE_PATH = os.getenv(
            "PROFILE_PATH",
            default=rf"C:\Users\{LOCAL_USER}\AppData\Local\Google\Chrome\User Data",
        )

        if kill_windows:
            if not skip_confirmation:
                input("Press any key to close Chrome and continue...")
            os.system("taskkill /f /im chrome.exe")
        options = webdriver.ChromeOptions()
        if CHROME_PROFILE is None:
            profiles = glob.glob(os.path.join(PROFILE_PATH, "Profile*"))
            if len(profiles) > 1:
                CHROME_PROFILE = profiles[-1].split(os.sep)[-1]
                print(
                    f'Warning: multiple Chrome profiles found. Using {CHROME_PROFILE}, if this is incorrect, add e.g. "CHROME_PROFILE = Profile 1" to .env'
                )
            else:
                CHROME_PROFILE = "Profile 1"

        options.add_argument(f"--user-data-dir={PROFILE_PATH}")
        options.add_argument(f"--profile-directory={CHROME_PROFILE}")
        svc = webdriver.ChromeService(
            executable_path=binary_path,
            capabilities=options.to_capabilities(),
        )

        self.driver = webdriver.Chrome(service=svc, options=options)

    def get_url_source(self, url):
        self.driver.get(url)
        self.driver.minimize_window()
        if "Log in" in self.driver.page_source:
            raise Exception(
                "Session has expired, please log in manually in Chrome first"
            )
        return BeautifulSoup(self.driver.page_source, features="html.parser")

    def wait_for_page_item(self, by, item, seconds=1):
        WebDriverWait(self.driver, seconds).until(
            EC.presence_of_element_located((by, item))
        )
        return BeautifulSoup(
            self.driver.find_element(by, item).get_attribute("innerHTML"),
            features="html.parser",
        )

    def close(self):
        self.driver.close()
        self.driver.quit()


class Browser:
    def __init__(self):
        self.browser = None

    def get_browser(self):
        if not self.browser:
            self.browser = _Browser()
        return self.browser
