import csv
import glob
import os
import sys

import psutil
import requests
from bs4 import BeautifulSoup
from chromedriver_py import binary_path
from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()


class NotConfiguredException(Exception):
    pass


class EdgeBrowser:
    """A browser that uses the Selenium Edge driver to load interactive webpages"""

    def __init__(
        self,
        kill_windows=True,
        skip_confirmation=False,
        minimise=True,
        use_profile=True,
        headless=False,
        debug=False,
    ):
        self.page = None
        self.kill_windows = kill_windows
        self.skip_confirmation = skip_confirmation
        self.minimise = minimise
        self.use_profile = use_profile
        self.headless = headless
        self.debug = debug

        logger.remove(0)
        if self.debug:
            logger.add(sys.stderr, level="DEBUG", format="{time} | {level} | {message}")
            logger.debug("Debug enabled")
        else:
            logger.add(
                sys.stderr, level="WARNING", format="{time} | {level} | {message}"
            )

        if self.use_profile and not self.kill_windows:
            logger.warning(
                "Combining use_profile=True and kill_windows=False will fail to open the correct profile if it is currently in use"
            )

        logger.debug("Creating Browser()")

        LOCAL_USER = os.getenv("LOCAL_USER")
        if not LOCAL_USER:
            raise NotConfiguredException("LOCAL_USER needs to defined in .env")
        PROFILE_PATH = os.getenv(
            "PROFILE_PATH",
            default=rf"C:\Users\{LOCAL_USER}\AppData\Local\Microsoft\Edge\User Data\Default",
        )
        bin_path = r"msedgedriver.exe"
        opts = webdriver.EdgeOptions()
        opts.add_argument("--no-sandbox")
        opts.use_chromium = True
        # opts.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        opts.add_argument(f"--user-data-dir={PROFILE_PATH}")
        opts.add_argument("--profile-directory=Default")
        self.driver = webdriver.Edge(
            options=opts, service=webdriver.EdgeService(executable_path=bin_path)
        )

    def wait_for_page_item(self, by, item, seconds):
        WebDriverWait(self.driver, timeout=seconds).until(
            EC.presence_of_element_located((by, item))
        )
        return BeautifulSoup(
            self.driver.find_element(by, item).get_attribute("innerHTML"),
            features="html.parser",
        )

    def get_url_source(self, url):
        self.driver.get(url)

    def get_browser(self):
        return self


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

    BY = By

    def __init__(
        self,
        kill_windows=True,
        skip_confirmation=False,
        minimise=True,
        use_profile=True,
        headless=False,
        debug=False,
    ):
        self.page = None
        self.kill_windows = kill_windows
        self.skip_confirmation = skip_confirmation
        self.minimise = minimise
        self.use_profile = use_profile
        self.headless = headless
        self.debug = debug

        logger.remove(0)
        if self.debug:
            logger.add(sys.stderr, level="DEBUG", format="{time} | {level} | {message}")
            logger.debug("Debug enabled")
        else:
            logger.add(
                sys.stderr, level="WARNING", format="{time} | {level} | {message}"
            )

        if self.use_profile and not self.kill_windows:
            logger.warning(
                "Combining use_profile=True and kill_windows=False will fail to open the correct profile if it is currently in use"
            )

        logger.debug("Creating Browser()")

        LOCAL_USER = os.getenv("LOCAL_USER")
        if not LOCAL_USER:
            raise NotConfiguredException("LOCAL_USER needs to defined in .env")
        CHROME_PROFILE = os.getenv("CHROME_PROFILE", default=None)
        logger.debug(f"LOCAL_USER set to {LOCAL_USER}")
        logger.debug(f"CHROME_PROFILE set to {CHROME_PROFILE}")

        if sys.platform == "darwin":
            logger.debug("Detected Mac OS")
            PNAME = "Google Chrome"
            PROFILE_PATH = os.getenv(
                "PROFILE_PATH",
                default=rf"/Users/{LOCAL_USER}/Library/Application Support/Google/Chrome",
            )
        else:
            logger.debug("Defaulting to Windows")
            PNAME = "chrome.exe"
            PROFILE_PATH = os.getenv(
                "PROFILE_PATH",
                default=rf"C:\Users\{LOCAL_USER}\AppData\Local\Google\Chrome\User Data",
            )
        if self.kill_windows:
            logger.debug("Killing windows...")
            if not skip_confirmation:
                input("Press any key to close Chrome and continue...")
            for proc in psutil.process_iter():
                if proc.name() == PNAME:
                    proc.kill()

        options = webdriver.ChromeOptions()

        if self.use_profile:
            logger.debug(f"PROFILE_PATH set to {PROFILE_PATH}")

            if CHROME_PROFILE is None:
                profiles = glob.glob(os.path.join(PROFILE_PATH, "Profile*"))
                if os.path.exists(os.path.join(PROFILE_PATH, "Default")):
                    CHROME_PROFILE = "Default"
                elif len(profiles) > 1:
                    CHROME_PROFILE = profiles[-1].split(os.sep)[-1]
                    logger.warning(
                        f'Warning: multiple Chrome profiles found. Using {CHROME_PROFILE}, if this is incorrect, add e.g. "CHROME_PROFILE = Profile 1" to .env'
                    )
                else:
                    CHROME_PROFILE = "Profile 1"
            logger.debug(f"CHROME_PROFILE set to {CHROME_PROFILE}")

            # options.add_argument(f"--user-data-dir={PROFILE_PATH}")
            options.add_argument(f"--profile-directory={PROFILE_PATH}/{CHROME_PROFILE}")
        if self.headless:
            logger.debug("Using headless mode")
            options.add_argument("--headless=new")
        svc = webdriver.ChromeService(
            executable_path=binary_path,
            # capabilities=options.to_capabilities(),
        )

        self.driver = webdriver.Chrome(service=svc, options=options)
        logger.debug("Finished creating Browser()")

    def get_page_source(self, url: str = None):
        logger.debug(f"Loading {url}...")
        try:
            if url:
                self.driver.get(url)
                if self.minimise:
                    self.driver.minimize_window()
            self.page = self.driver.page_source
            return BeautifulSoup(str(self.page), features="html.parser")
        except exceptions.InvalidSessionIdException as e:
            logger.critical(
                "Selenium encountered an error. Enable debugging to see more"
            )
            logger.debug(str(e))
            return None

    def wait_for_page_item(self, by, item, seconds=1):
        WebDriverWait(self.driver, seconds).until(
            EC.presence_of_element_located((by, item))
        )
        return BeautifulSoup(
            self.driver.find_element(by, item).get_attribute("innerHTML"),
            features="html.parser",
        )

    def close(self):
        try:
            logger.debug("Closing Browser()")
            self.driver.close()
            self.driver.quit()
            logger.debug("Browser() closed!")
        except exceptions.InvalidSessionIdException:
            # Session is already closed
            pass


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
