#!/usr/bin/env python3
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

# pylint: disable=duplicate-code
# Bootstrap must precede third-party imports to select the installed environment.
# pylint: disable=wrong-import-order

from project_env import run_in_project_venv

if __name__ == "__main__":
    run_in_project_venv(__file__)

import sys
import os
import argparse
import json
from pathlib import Path
import subprocess
import time

import yaml
from colorama import init, Fore
from seleniumbase import BaseCase
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv, find_dotenv
from supl.filters import FilterPolicy, add_filter_arguments, parse_date
from supl.jobs import prepare_download, publish_xml

# Load the .env file (by default, it looks in the current working directory)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Retrieve the variable
so_user = os.getenv("SO_USER")
so_pass = os.getenv("SO_PASS")

CONFIG = "config.yaml"
JOB_CONTEXT = "SO_SUPL_JOB_CONTEXT"

# Init the colorama (colored output)
init(autoreset=True)


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
        - Publishes the XML together with its per-run filter snapshot.

        Raises:
            Exception: If the XML cannot be published safely.

        Example:
            >>> self.test_recording()
            # Logs in, downloads, and moves the XML file.
        """

        conf, report_date, policy = runtime_job()
        self.custom_date = report_date.strftime("%d.%m.%Y")

        # Open the starting pages (adjust these URLs as needed)
        self.open("https://www.skolaonline.cz/prihlaseni/?")
        self.type("#JmenoUzivatele", so_user)
        self.type("#HesloUzivatele", so_pass)
        self.click("#btnLogin")

        self.click_if_visible("button#ctl00_ctl16_NeprecteneZpravyOtazka_btnPozdeji")
        self.click_if_visible("button#c-p-bn")

        self.open(
            "https://aplikace.skolaonline.cz/SOL/App/TiskoveSestavy/KTS004_Filtr.aspx"
            "?SestavaID="
                "84ad1259-cfd8-417a-ab4e-7287846a6873"
            "&ReturnPage="
                "/SOL/App/TiskoveSestavy/KTS003_SeznamSestav.aspx"
            "?SlozkaID="
                "00000000-0000-0000-0000-000000000000&page=1"
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

        self.type("input#FiltrGrid_tb", self.custom_date)
        self.click("button#ExportXmlDataButton")

        #   This part moves the downloaded file into the desired folder
        #    as the SeleniumBase {PyTest} doesn't really like changing
        #    the default folder.
        download_dir = self.get_downloads_folder()
        os.makedirs(download_dir, exist_ok=True)
        print(Fore.YELLOW + "Download directory: " + download_dir)

        xml_file = None
        try:
            xml_file = self._wait_for_xml_download(download_dir)
        except TimeoutError as exc:
            print(Fore.RED + str(exc))
        except FileNotFoundError:
            print(Fore.YELLOW + "Selenium did not recreate the download folder.")

        if xml_file:
            print(Fore.MAGENTA + "Downloaded XML file: " + xml_file)
            destination = publish_xml(Path(xml_file).read_bytes(), report_date, conf, policy)
            Path(xml_file).unlink()
            print(Fore.GREEN + "XML file copied to: " + destination)
        else:
            print(Fore.YELLOW + "No XML file was downloaded.")

    def _wait_for_xml_download(self, download_dir, timeout=60):
        """Polls the SeleniumBase downloads folder until a finalized XML appears."""
        deadline = time.time() + timeout
        last_file = None
        last_size = -1
        stable_reads = 0

        while time.time() < deadline:
            os.makedirs(download_dir, exist_ok=True)
            try:
                files = os.listdir(download_dir)
            except FileNotFoundError:
                files = []

            xml_files = [
                os.path.join(download_dir, f)
                for f in files
                if f.lower().endswith(".xml")
            ]
            cr_files = [
                f for f in files if f.lower().endswith(".crdownload")
            ]

            if xml_files:
                xml_files.sort(key=os.path.getmtime, reverse=True)
                newest = xml_files[0]
                try:
                    size = os.path.getsize(newest)
                except FileNotFoundError:
                    time.sleep(0.5)
                    continue
                if newest == last_file and size == last_size and not cr_files:
                    stable_reads += 1
                    if stable_reads >= 2:
                        return newest
                else:
                    last_file = newest
                    last_size = size
                    stable_reads = 0

            time.sleep(1)

        raise TimeoutError(
            f"XML download did not complete within {timeout} seconds."
        )


def runtime_job():
    """The pytest subprocess receives the parent's frozen policy via its env."""
    context = os.getenv(JOB_CONTEXT)
    if context is None:
        return prepare_download(CONFIG, os.getenv("DATE_TO_PROCESS"))
    data = json.loads(context)
    report_date = parse_date(data["date"])
    policy = FilterPolicy.from_dict(data["filters"])
    return {"settings": {"watch_folder": data["watch_folder"]}}, report_date, policy


def build_parser():
    """Describe download/filter arguments while leaving pytest options intact."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date", help="Provide date for the script to get", default=None
    )
    add_filter_arguments(parser)
    return parser


def main():
    """Launch the browser downloader with an immutable per-run filter snapshot."""
    parser = build_parser()

    # Parse known args and leave the rest for SeleniumBase/pytest
    args, remaining_args = parser.parse_known_args()

    try:
        config, report_date, policy = prepare_download(
            CONFIG, args.date or os.getenv("DATE_TO_PROCESS"), args
        )
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    context = {"date": report_date.isoformat(), "filters": policy.to_dict(),
               "watch_folder": config["settings"].get("watch_folder", "./watch")}
    previous = os.environ.get(JOB_CONTEXT)
    try:
        os.environ[JOB_CONTEXT] = json.dumps(context)
        # Equivalent to BaseCase.main, while preserving the subprocess exit code.
        return subprocess.call([sys.executable, "-m", "pytest", __file__, "-s", *remaining_args])
    finally:
        if previous is None:
            os.environ.pop(JOB_CONTEXT, None)
        else:
            os.environ[JOB_CONTEXT] = previous


if __name__ == "__main__":
    raise SystemExit(main())
