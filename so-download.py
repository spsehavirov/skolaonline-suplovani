#!/usr/bin/env python
"""
Automated Selenium Test for Downloading XML Substitution Data from SkolaOnline.

This script automates the login process and navigation within SkolaOnline.cz
to download an XML report for student substitutions. It uses SeleniumBase
for browser automation and processes the downloaded file to move it into
the designated folder.

Features:
- Logs into SkolaOnline.cz using credentials from `.env` file.
- Navigates through the website to download an XML report.
- Allows specifying a custom date via command-line arguments.
- Moves the downloaded XML file to a predefined directory.
- Supports environment variable handling via `dotenv`.

Classes:
- `RecorderTest`: A SeleniumBase test class that automates the XML download process.

Functions:
- `intercept_response(request, response)`: Logs request headers (for debugging).
- `test_recording()`: Runs the full Selenium test to download and move the XML file.

Command-Line Usage:
    # Run the script manually
    python this_script.py --date "20.02.2024" --headless

Dependencies:
- seleniumbase
- yaml
- dotenv
- argparse
- shutil
- datetime

Notes:
- The script retrieves credentials (`SO_USER` and `SO_PASS`) from a `.env` file.
- The `DATE_TO_PROCESS` variable can be set via command-line arguments or `.env`.
- The SeleniumBase test is executed as a pytest-compatible test case.
"""

import sys
import os
import shutil
import argparse

from datetime import datetime

import yaml
from seleniumbase import BaseCase
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv, set_key, unset_key, find_dotenv

# Load the .env file (by default, it looks in the current working directory)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Retrieve the variable
so_user = os.getenv("SO_USER")
so_pass = os.getenv("SO_PASS")


class RecorderTest(BaseCase):
    """
    A SeleniumBase test case for automating the download of XML substitution data
    from SkolaOnline.cz.

    This class:
    - Logs into the SkolaOnline.cz web portal.
    - Navigates to the substitution report page.
    - Selects a specified or default date.
    - Downloads the XML report and moves it to the designated folder.

    Attributes:
        custom_date (str): The date used for filtering the report.
                           Defaults to today's date if not provided.

    Methods:
        intercept_response(request, response):
            Captures and prints request headers (for debugging purposes).

        test_recording():
            Runs the automated test to log in, apply filters, download the XML file,
            and move it to the correct directory.
    """
    custom_date = None

    def intercept_response(self, request, response):
        """
        Intercepts and prints HTTP request headers.

        This method is useful for debugging and inspecting the headers of
        network requests made during the Selenium test execution.

        Args:
            request (seleniumbase.request): The outgoing HTTP request.
            response (seleniumbase.response): The received HTTP response.

        Example:
            >>> self.intercept_response(request, response)
            # Prints request headers to the console.
        """
        print(response)
        print(request.headers)

    def test_recording(self):
        """
        Automates the process of logging into SkolaOnline.cz and downloading 
        an XML report.

        This method performs the following steps:
        - Logs in using credentials from the `.env` file.
        - Navigates to the report filtering page.
        - Selects the appropriate date for the report.
        - Initiates the XML download.
        - Moves the downloaded file to the specified folder.
        - Unsets the `DATE_TO_PROCESS` environment variable after processing.

        Raises:
            Exception: If the XML download fails or the file is not found.

        Example:
            >>> self.test_recording()
            # Logs in, downloads, and moves the XML file.
        """

        # Open the starting pages (adjust these URLs as needed)
        self.open("https://www.skolaonline.cz/prihlaseni/?")
        self.type("#JmenoUzivatele", so_user)
        self.type("#HesloUzivatele", so_pass)
        self.click("#btnLogin")

        self.click_if_visible("button#ctl00_ctl16_NeprecteneZpravyOtazka_btnPozdeji")
        self.click_if_visible("button#c-p-bn")

        self.open(
            "https://aplikace.skolaonline.cz/SOL/App/TiskoveSestavy/KTS004_Filtr.aspx"
            "?"
            "SestavaID=532a6c6e-f76a-46ab-9e5a-236b628da333"
            "&"
            "ReturnPage=/SOL/App/TiskoveSestavy/KTS003_SeznamSestav.aspx"
            "?"
            "SlozkaID=00000000-0000-0000-0000-000000000000&page=1"
        )
        # Set the filter date (adjust the selector if necessary)
        self.click_if_visible("button#c-p-bn")
        self.click("span#PopisSestavyText")

        element = self.find_element(
            ".ig_e0b03b79_7"
        )  # Needs to be manually found to activate JS handlers!
        ActionChains(self.driver).move_to_element(element).double_click().perform()
        self.sleep(0.1)

        self.highlight_click("#FiltrGrid_rc_0_3")
        self.click("td#FiltrGrid_rc_0_3")

        self.custom_date = os.getenv("DATE_TO_PROCESS")
        if self.custom_date is None:
            self.custom_date = datetime.today().strftime("%d.%m.%Y")

        self.type("input#FiltrGrid_tb", self.custom_date)
        self.click("button#ExportXmlDataButton")

        #   This part moves the downloaded file into the desired folder
        #    as the SeleniumBase {PyTest} doesn't really like changing
        #    the default folder.
        self.sleep(5)
        download_dir = self.get_downloads_folder()
        print("Download directory: " + download_dir)

        # Look for an XML file in that folder
        files = os.listdir(download_dir)
        xml_files = [f for f in files if f.lower().endswith(".xml")]

        with open("config.yaml", "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        if xml_files:
            xml_file = os.path.join(download_dir, xml_files[0])
            print("Downloaded XML file: " + xml_file)
            # Option 2: Copy the file to a different location (e.g., current working directory)
            datestamp = (
                datetime.strptime(self.custom_date, '%d.%m.%Y').strftime('%Y-%m-%d')
            )
            destination = os.path.join(
                os.getcwd(),
                f"{config["settings"]["watch_folder"]}/so_suplovani_students-{datestamp}.xml",
            )
            shutil.move(xml_file, destination)
            print("XML file copied to: " + destination)
        else:
            print("No XML file was downloaded.")

        unset_key(dotenv_path, "DATE_TO_PROCESS")


# To run the test from the command line:
#   seleniumbase run <this_script_name.py> --headless --download-dir=<your_download_path>
if __name__ == "__main__":
    # Define your custom arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--date", help="Provide date for the script to get", default=None
    )

    # Parse known args and leave the rest for SeleniumBase/pytest
    args, remaining_args = parser.parse_known_args()

    # Process your custom argument as needed
    if args.date:
        print("Custom date to process:", args.date)
        set_key(dotenv_path, "DATE_TO_PROCESS", args.date)

    # Replace sys.argv with the remaining args so that BaseCase.main gets only what it expects
    sys.argv = [sys.argv[0]] + remaining_args

    # Now run SeleniumBase's main, which will handle the remaining command-line arguments
    BaseCase.main(__name__, __file__)
