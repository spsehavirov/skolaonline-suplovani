#!/usr/bin/env python

import sys
import os
import yaml
import shutil
import argparse

from datetime import datetime
from dotenv import load_dotenv, set_key, unset_key, find_dotenv
from seleniumbase import BaseCase
from selenium.webdriver.common.action_chains import ActionChains

# Load the .env file (by default, it looks in the current working directory)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Retrieve the variable
so_user = os.getenv("SO_USER")
so_pass = os.getenv("SO_PASS")
date = None

class RecorderTest(BaseCase):
    custom_date = None

    def setUp(self):
        super().setUp()
        # Register the response interceptor so it’s used for all requests.
        #self.set_response_interceptor(self.intercept_response)

    def intercept_response(request, response):
        print(request.headers)

    def test_recording(self):
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

        element = self.find_element(".ig_e0b03b79_7") # Needs to be manually found to activate JS handlers!
        ActionChains(self.driver).move_to_element(element).double_click().perform()
        self.sleep(0.1)

        self.highlight_click("#FiltrGrid_rc_0_3")
        self.click("td#FiltrGrid_rc_0_3")

        self.custom_date = os.getenv("DATE_TO_PROCESS")
        if self.custom_date is None:
            self.custom_date = datetime.today().strftime('%d.%m.%Y')

        self.type("input#FiltrGrid_tb", self.custom_date)
        self.click("button#ExportXmlDataButton")

        """
            This part moves the downloaded file into the desired folder
            as the SeleniumBase {PyTest} doesn't really like changing
            the default folder.
        """

        download_dir = self.get_downloads_folder()
        print("Download directory: " + download_dir)

        # Look for an XML file in that folder
        files = os.listdir(download_dir)
        xml_files = [f for f in files if f.lower().endswith(".xml")]

        with open("config.yaml", "r") as config_file:
            config = yaml.safe_load(config_file)

        if xml_files:
            xml_file = os.path.join(download_dir, xml_files[0])
            print("Downloaded XML file: " + xml_file)
            # Option 2: Copy the file to a different location (e.g., current working directory)
            destination = os.path.join(os.getcwd(), f"{config["settings"]["watch_folder"]}/so_suplovani_students-{datetime.strptime(self.custom_date, '%d.%m.%Y').strftime('%Y-%m-%d')}.xml")
            shutil.move(xml_file, destination)
            print("XML file copied to: " + destination)
        else:
            print("No XML file was downloaded.")

        unset_key(dotenv_path, "DATE_TO_PROCESS")

# To run the test from the command line:
#   seleniumbase run <this_script_name.py> --headless --download-dir=<your_download_path>
if __name__ == '__main__':
    # Define your custom arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--date",
        help="Provide date for the script to get",
        default=None
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
