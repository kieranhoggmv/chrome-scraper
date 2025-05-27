import csv
import glob
import os
import sys
from typing import Literal

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

    def get_tables(self, source: BeautifulSoup) -> list:
        """Returns a list of the tables found on the page"""
        if not source:
            source = BeautifulSoup(str(self.page), features="html.parser")

        tables = source.find_all("table")
        table_list = []

        if tables:
            for i, table in enumerate(tables):
                this_table = []
                th = table.find_all("th")  # type: ignore
                if th:
                    this_table.append(
                        [",".join([heading.text.strip() for heading in th])]
                    )

                rows = table.find_all("tr")  # type: ignore
                for row in rows:
                    td = row.find_all("td")  # type: ignore
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
    driver_type = webdriver.Chrome
    service_type = webdriver.ChromeService

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
            logger.add(sys.stderr, level="DEBUG")
            logger.debug("Debug enabled")
            logger.debug(f"Settings: {self.driver_type}, {self.service_type}")
        else:
            logger.add(sys.stderr, level="WARNING")

        if self.use_profile and not self.kill_windows:
            logger.warning(
                "Combining use_profile=True and kill_windows=False will fail to open the correct profile if it is currently in use"
            )

        if not os.getenv("LOCAL_USER", None):
            raise NotConfiguredException("LOCAL_USER needs to defined in .env")
        self.profile_path = self.get_profile_path()
        logger.debug(self.profile_path)
        # self.local_user = self.get_profile_name(profile_path=self.profile_path)

        logger.debug(self.profile_path)

        options = self.get_options()

        if self.kill_windows:
            self.kill_open_windows()

        svc = self.service_type(
            # executable_path=binary_path,
            # capabilities=options.to_capabilities(),
        )

        logger.debug(f"Creating Browser() with {self.driver_type}")
        self.driver = self.driver_type(service=svc, options=options)  # type: ignore
        logger.debug(f"Finished creating Browser() {self.driver}")

    def kill_open_windows(self):
        if self.get_platform() == "macos":
            PNAME = "Google Chrome"
        else:
            PNAME = "chrome.exe"

        if self.kill_windows:
            logger.debug("Killing windows...")
            if not self.skip_confirmation:
                input("Press any key to close open windows and continue...")
            for proc in psutil.process_iter():
                if proc.name() == PNAME:
                    proc.kill()

    def get_options(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            logger.debug("Using headless mode")
            options.add_argument("--headless=new")
        if self.use_profile:
            logger.debug("Using existing profile")
        options.add_argument(f"--user-data-dir={self.profile_path}")

        # options.add_argument(f"--profile-directory={PROFILE_PATH}/{CHROME_PROFILE}")
        return options

    def get_profile_path(self):
        local_user = os.getenv("LOCAL_USER", None)

        if self.get_platform() == "macos":
            profile_path = os.getenv(
                "PROFILE_PATH",
                default=rf"/Users/{local_user}/Library/Application Support/Google/Chrome",
            )
        else:
            if self.use_profile:
                profile_path = os.getenv(
                    "PROFILE_PATH",
                    default=rf"C:\Users\{local_user}\AppData\Local\Google\Chrome\User Data",
                )
            else:
                profile_path = rf"C:\Users\{local_user}\AppData\Temp"
        return profile_path

    def get_platform(self) -> Literal["macos", "windows"]:
        platform = "windows"
        if sys.platform == "darwin":
            logger.debug("Detected Mac OS")
            platform = "macos"
        else:
            logger.debug("Defaulting to Windows")
        return platform

    def get_profile_name(self, profile_path):
        local_user = os.getenv("LOCAL_USER", None)
        profile = "Profile 1"

        if self.use_profile:
            if local_user is None:
                profiles = glob.glob(os.path.join(profile_path, "Profile*"))
                if os.path.exists(os.path.join(profile_path, "Default")):
                    profile = "Default"
                elif len(profiles) > 1:
                    profile = profiles[-1].split(os.sep)[-1]
                    logger.warning(
                        f'Warning: multiple Chrome profiles found. Using {profile}, if this is incorrect, add e.g. "CHROME_PROFILE = Profile 1" to .env'
                    )
                else:
                    profile = "Profile 1"
                return profile
            else:
                profile = local_user
        return profile

    def get_page_source(self, url: str):  # type: ignore
        logger.debug(f"Loading {url}...")
        try:
            if url:
                self.driver.get(url)  # type: ignore
                if self.minimise:
                    self.driver.minimize_window()  # type: ignore
            self.page = self.driver.page_source
            return BeautifulSoup(str(self.page), features="html.parser")
        except exceptions.InvalidSessionIdException as e:
            logger.critical(
                "Selenium encountered an error. Enable debugging to see more"
            )
            logger.debug(str(e))
            return None

    def wait_for_page_item(self, by, item, seconds=1):
        WebDriverWait(self.driver, seconds).until(  # type: ignore
            EC.presence_of_element_located((by, item))
        )
        return BeautifulSoup(
            self.driver.find_element(by, item).get_attribute("innerHTML"),  # type: ignore
            features="html.parser",
        )

    def wait_for_element_by_id(self, elem_id, seconds=1):
        return self.wait_for_page_item(By.ID, id, seconds)

    def wait_for_element_by_class(self, css_class, seconds=1):
        return self.wait_for_page_item(By.CLASS_NAME, css_class, seconds)

    def wait_for_element_by_tag(self, html_tag, seconds=1):
        return self.wait_for_page_item(By.TAG_NAME, html_tag, seconds)

    def close(self):
        try:
            logger.debug("Closing Browser()")
            self.driver.close()  # type: ignore
            self.driver.quit()  # type: ignore
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


class EdgeBrowser(Browser):
    """A browser that uses the Selenium Edge driver to load interactive webpages"""

    def __init__(self, *args, **kwargs):
        self.bin_path = r"msedgedriver.exe"
        # service = webdriver.EdgeService(executable_path=bin_path)
        self.driver_type = webdriver.Edge
        self.service_type = webdriver.EdgeService
        super().__init__(*args, **kwargs)

    def get_default_profile_path(self):
        return r"C:\Users\{}\AppData\Local\Microsoft\Edge\User Data\Default"

    def get_options(self):  # type: ignore
        opts = webdriver.EdgeOptions()
        opts.add_argument("--no-sandbox")
        # opts.use_chromium = True
        opts.binary_location = (
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        )
        if self.use_profile:
            opts.add_argument(f"--user-data-dir={self.profile_path}")
            opts.add_argument("--profile-directory=Default")
        return opts

    def kill_open_windows(self):
        process_name = "edge.exe"

        if self.kill_windows:
            logger.debug("Killing windows...")
            if not self.skip_confirmation:
                input("Press any key to close open windows and continue...")
            for proc in psutil.process_iter():
                try:
                    if proc.name() == process_name:
                        proc.kill()
                except psutil.NoSuchProcess:
                    pass
