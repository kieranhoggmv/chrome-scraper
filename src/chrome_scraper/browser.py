from contextlib import contextmanager
import glob
from bs4 import BeautifulSoup
import csv
from dotenv import load_dotenv
import psutil
import os
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from chromedriver_py import binary_path

load_dotenv()


class NotConfiguredException(Exception):
    pass


class BrowserSingleton:
    BY = By

    def __init__(self, kill_windows=True, skip_confirmation=False):
        LOCAL_USER = os.getenv("LOCAL_USER")
        if not LOCAL_USER:
            raise NotConfiguredException("LOCAL_USER needs to defined in .env")
        CHROME_PROFILE = os.getenv("CHROME_PROFILE", default=None)

        if sys.platform == "darwin":
            PNAME = "Google Chrome"
            PROFILE_PATH = os.getenv(
                "PROFILE_PATH",
                default=rf"/Users/{LOCAL_USER}/Library/Application Support/Google/Chrome",
            )
        else:
            PNAME = "chrome.exe"
            PROFILE_PATH = os.getenv(
                "PROFILE_PATH",
                default=rf"C:\Users\{LOCAL_USER}\AppData\Local\Google\Chrome\User Data",
            )

        if kill_windows:
            if not skip_confirmation:
                input("Press any key to close Chrome and continue...")
                for proc in psutil.process_iter():
                    if proc.name() == PNAME:
                        proc.kill()
        options = webdriver.ChromeOptions()
        if CHROME_PROFILE is None:
            profiles = glob.glob(os.path.join(PROFILE_PATH, "Profile*"))
            if os.path.exists(os.path.join(PROFILE_PATH, "Default")):
                CHROME_PROFILE = "Default"
            elif len(profiles) > 1:
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
        return BeautifulSoup(self.driver.page_source, features="html.parser")

    def wait_for_page_item(self, by, item, seconds=1):
        WebDriverWait(self.driver, seconds).until(
            EC.presence_of_element_located((by, item))
        )
        return BeautifulSoup(
            self.driver.find_element(by, item).get_attribute("innerHTML"),
            features="html.parser",
        )

    def save_tables(self):
        """
        Exports each table found on the source page to a CSV file
        """
        bs = BeautifulSoup(self.driver.page_source, features="html.parser")
        tables = bs.find_all("table")
        for i, table in enumerate(tables):
            with open(f"table{i + 1}.csv", "w") as csv_file:
                csv_writer = csv.writer(csv_file)
                th = table.find_all("th")
                if th:
                    csv_writer.writerow(
                        [",".join([heading.text.strip() for heading in th])]
                    )
                rows = table.find_all("tr")
                for row in rows:
                    td = row.find_all("td")
                    if td:
                        csv_writer.writerow(
                            [",".join([cell.text.strip() for cell in td])]
                        )


class Browser:
    def __init__(self, kill_windows=True, skip_confirmation=False):
        self.browser = None
        self.kill_windows = kill_windows
        self.skip_confirmation = skip_confirmation

    @contextmanager
    def get_browser(self) -> BrowserSingleton:
        if not self.browser:
            self.browser = BrowserSingleton(self.kill_windows, self.skip_confirmation)
        try:
            yield self.browser
        finally:
            self.close()

    def close(self):
        self.browser.driver.close()
        self.browser.driver.quit()
