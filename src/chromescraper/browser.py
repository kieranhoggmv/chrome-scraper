import csv
import glob
import os
import sys
from contextlib import contextmanager

import psutil
import requests
from bs4 import BeautifulSoup
from chromedriver_py import binary_path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()


class NotConfiguredException(Exception):
    pass


class SimpleBrowser:
    """A browser to get the source of simple webpages"""

    def __init__(self):
        self.page = None

    def get_page_source(self, url) -> BeautifulSoup:
        """Loads a URL and returns its source code as a BeautifulSoup object"""
        r = requests.get(url)
        if r.ok:
            self.page = r.text
        else:
            self.page = None
        return BeautifulSoup(str(self.page), features="html.parser")

    def get_tables(self, source: BeautifulSoup = None) -> list:
        """Returns a list of the tables found on the page"""
        if not source:
            source = BeautifulSoup(str(self.page), features="html.parser")

        tables = source.find_all("table")
        table_list = []

        if tables:
            for i, table in enumerate(tables):
                this_table = []
                th = table.find_all("th")
                if th:
                    this_table.append(
                        [",".join([heading.text.strip() for heading in th])]
                    )

                rows = table.find_all("tr")
                for row in rows:
                    td = row.find_all("td")
                    if td:
                        this_table.append(
                            [",".join([cell.text.strip() for cell in td])]
                        )
                table_list.append(this_table)
        else:
            print("No tables found")
        return table_list


class Browser(SimpleBrowser):
    """A browser that uses the Selenium Chrome driver to load interactive webpages"""

    _instance = None
    BY = By

    @contextmanager
    def __new__(
        cls,
        kill_windows: bool = True,
        skip_confirmation: bool = False,
        minimise: bool = True,
    ):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.setup(cls, kill_windows, skip_confirmation, minimise)
        try:
            yield cls._instance
        finally:
            cls.close(cls)

    def setup(self, kill_windows=True, skip_confirmation=False, minimise=True):
        self.page = None
        self.kill_windows = kill_windows
        self.skip_confirmation = skip_confirmation
        self.minimise = minimise

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

    def get_page_source(self, url: str = None):
        if url:
            self.driver.get(url)
            if self.minimise:
                self.driver.minimize_window()
        self.page = self.driver.page_source
        return BeautifulSoup(str(self.page), features="html.parser")

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


def list_dimensions(a):
    return (
        [len(a)] + list_dimensions(a[0]) if (isinstance(a, list) and len(a) > 0) else []
    )


def to_csv(source_list: list, number: int = 1) -> None:
    """
    Saves a list containing one or more comma-separated values to a csv file
    """
    dimensions = list_dimensions(source_list)
    if len(dimensions) > 2:
        to_csv(source_list[0], number)
        to_csv(source_list[1:], number + 1)
    elif len(source_list) > 0:
        with open(f"table-{number}.csv", "w") as csv_file:
            csv_writer = csv.writer(csv_file)
            for row in source_list:
                csv_writer.writerow(row)
