#!/usr/bin/env python
"""
Lightweight downloader for ŠkolaOnline substitution XML without Selenium.

The original `so_download.py` script drives a browser to click through the
report filter screen. This version performs the same steps with direct HTTP
requests:
1. Log in using the public login form on skolaonline.cz.
2. Load the substitution filter page to collect the server-side viewstate key.
3. Post the filter form with the requested date and trigger the "Exportuj XML"
   button, saving the returned XML to the configured watch folder.

Credentials are loaded from `.env` (`SO_USER`, `SO_PASS`). The output filename
matches the Selenium variant: `so_suplovani_students-YYYY-MM-DD.xml`.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import Optional, Tuple

import requests
import yaml
from bs4 import BeautifulSoup
from colorama import Fore, init
from dotenv import find_dotenv, load_dotenv, set_key, unset_key
from requests_toolbelt import MultipartEncoder

# Constants used by the SkolaOnline form flow
LOGIN_URL = "https://aplikace.skolaonline.cz/SOL/Prihlaseni.aspx"
FILTER_URL = (
    "https://aplikace.skolaonline.cz/SOL/App/TiskoveSestavy/KTS004_Filtr.aspx"
    "?SestavaID=532a6c6e-f76a-46ab-9e5a-236b628da333"
    "&ReturnPage=/SOL/App/TiskoveSestavy/KTS003_SeznamSestav.aspx"
    "?SlozkaID=00000000-0000-0000-0000-000000000000&page=1"
)
CONFIG = "config.yaml"

# Init color output once
init(autoreset=True)

# Load the .env file (by default, it looks in the current working directory)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Retrieve credentials
SO_USER = os.getenv("SO_USER")
SO_PASS = os.getenv("SO_PASS")


class DownloadError(RuntimeError):
    """Custom error when the download fails."""


def _parse_date(date_str: Optional[str]) -> datetime:
    """
    Parse the user-provided date into a datetime.date.
    Accepts common dot and dash separated formats used in the repo.
    """
    if not date_str:
        return datetime.today()

    candidates = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]
    for fmt in candidates:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {date_str}")


def _ensure_credentials() -> None:
    if not SO_USER or not SO_PASS:
        raise DownloadError("Missing SO_USER or SO_PASS in the .env file.")


def _login(session: requests.Session) -> None:
    """Authenticate with the same form the Selenium script fills."""
    payload = {
        "JmenoUzivatele": SO_USER,
        "HesloUzivatele": SO_PASS,
        "btnLogin": "Přihlásit do aplikace",
    }
    resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=20)
    if resp.status_code != 200 or ".ASPXAUTH" not in session.cookies:
        raise DownloadError("Login failed; check credentials or site availability.")


def _fetch_form_state(session: requests.Session) -> Tuple[str, str, str]:
    """
    Load the filter page and return
    (viewstate_session_key, current_date, row_datakey).
    The server stores the heavy viewstate on its side and references it via the key.
    """
    resp = session.get(FILTER_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    viewstate_el = soup.find("input", {"name": "__VIEWSTATE_SESSION_KEY"})
    date_el = soup.find("input", {"id": "wdcDatum_input"})
    row = soup.find("tr", {"id": "FiltrGrid_r_0"})

    viewstate_session_key = viewstate_el.get("value", "") if viewstate_el else ""
    current_date = date_el.get("value", "") if date_el else ""
    row_datakey = row.get("datakey", "") if row else ""

    if not viewstate_session_key or not current_date or not row_datakey:
        raise DownloadError("Failed to extract form tokens from the filter page.")

    return viewstate_session_key, current_date, row_datakey


def _download_xml(session: requests.Session, date_value: str) -> bytes:
    """
    Trigger the export button via POST and return the XML payload as bytes.
    """
    viewstate_session_key, page_date, row_datakey = _fetch_form_state(session)

    page_date_dt = datetime.strptime(page_date, "%d.%m.%Y")

    # Replicates the client-side grid state that stores the date filter.
    layout_xml = (
        "<DisplayLayout>"
        "<StateChanges>"
        f'<StateChange Type="ActiveCell" Level="0_3" DataKey="{row_datakey}"></StateChange>'
        f'<StateChange Type="ChangedCells" Value="{date_value}" Level="0_3" '
        f'DataKey="{row_datakey}"></StateChange>'
        "</StateChanges>"
        "</DisplayLayout>"
    )
    encoded_layout = requests.utils.quote(layout_xml, safe="")

    # Date chooser hidden value wants the XML snippet already URL-encoded.
    encoded_date_hidden = requests.utils.quote(
        f'<DateChooser Value="{page_date_dt.strftime("%Yx%mx%d")}"></DateChooser>',
        safe="",
    )
    dp_cal_value = requests.utils.quote(
        f'<x PostData="{page_date_dt.strftime("%Yx%mx-1x-1x-1")}"></x>',
        safe="",
    )

    fields = {
        "__EVENTTARGET": "ctl00$main$ExportXmlDataButton",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "",  # actual state is referenced by the session key
        "__VIEWSTATE_SESSION_KEY": viewstate_session_key,
        "FiltrGrid": encoded_layout,
        "ctl00$hdnSessionKey": "",
        "wdcDatum_input": page_date,
        "ctl00$main$DatumGenerovani$wdcDatum_hidden": encoded_date_hidden,
        "DP_CAL_ID_1": dp_cal_value,
        "ctl00$main$ExportXmlDataButton": "Exportuj XML data",
    }

    encoder = MultipartEncoder(fields=fields)
    resp = session.post(
        FILTER_URL,
        data=encoder,
        headers={"Content-Type": encoder.content_type},
        allow_redirects=False,
        timeout=30,
    )
    if resp.status_code != 200:
        raise DownloadError(f"Export failed with status {resp.status_code}.")

    if not resp.text.lstrip().startswith("<NewDataSet"):
        raise DownloadError("Unexpected response while downloading XML data.")

    return resp.content


def _save_xml(content: bytes, date_obj: datetime, config: dict) -> str:
    """Persist the downloaded XML into the configured watch folder."""
    datestamp = date_obj.strftime("%Y-%m-%d")
    watch_folder = config["settings"].get("watch_folder", "./watch")
    os.makedirs(watch_folder, exist_ok=True)
    destination = os.path.join(
        os.getcwd(), f"{watch_folder}/so_suplovani_students-{datestamp}.xml"
    )
    with open(destination, "wb") as xml_file:
        xml_file.write(content)
    return destination


def _update_config_from_args(args: argparse.Namespace) -> dict:
    """Keep include/exclude behavior consistent with the Selenium script."""
    if os.path.exists(CONFIG):
        with open(CONFIG, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    else:
        config = {"settings": {}, "include": [], "exclude": []}

    config.setdefault("settings", {})
    config["settings"].setdefault("exclude", [])
    config["settings"].setdefault("include", [])

    if args.clear:
        print(Fore.YELLOW + "Cleared all include/exclude rules")
        config["settings"]["exclude"] = []
        config["settings"]["include"] = []

    if args.include:
        print(Fore.GREEN + f"Include: {args.include}")
        include_list = [item.strip().upper() for item in args.include.split(",")]
        config["settings"]["include"].extend(include_list)

    if args.exclude:
        print(Fore.RED + f"Exclude: {args.exclude}")
        exclude_list = [item.strip().upper() for item in args.exclude.split(",")]
        config["settings"]["exclude"].extend(exclude_list)

    if args.day_end_hour is not None:
        config["settings"]["day_end_hour"] = int(args.day_end_hour)

    with open(CONFIG, "w", encoding="utf-8") as config_file:
        yaml.safe_dump(
            config, config_file, default_flow_style=False, allow_unicode=True
        )

    return config


def main() -> None:
    """Download substitution XML via direct HTTP requests (no Selenium)."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help='Date to download (e.g. "25.02.2025").')
    parser.add_argument(
        "--include", help="Comma-separated list of items to include", default=None
    )
    parser.add_argument(
        "--exclude", help="Comma-separated list of items to exclude", default=None
    )
    parser.add_argument(
        "--clear",
        help="Clear include/exclude lists before adding new values",
        action="store_true",
    )
    parser.add_argument(
        "--day-end-hour",
        help="Only include substitutions up to this school period (e.g. 4).",
        type=int,
        default=None,
    )
    args = parser.parse_args()

    custom_date = args.date or os.getenv("DATE_TO_PROCESS")
    if custom_date:
        print("Custom date to process:", Fore.CYAN + custom_date)
        set_key(dotenv_path, "DATE_TO_PROCESS", custom_date)

    config = _update_config_from_args(args)

    # Prepare date formatting
    date_obj = _parse_date(custom_date)
    date_for_form = date_obj.strftime("%d.%m.%Y")

    try:
        _ensure_credentials()
        with requests.Session() as session:
            _login(session)
            xml_content = _download_xml(session, date_for_form)
        saved_path = _save_xml(xml_content, date_obj, config)
        print(Fore.GREEN + f"XML file saved to: {saved_path}")
    except (requests.RequestException, DownloadError, ValueError) as exc:
        print(Fore.RED + f"Download failed: {exc}")
    finally:
        unset_key(dotenv_path, "DATE_TO_PROCESS")


if __name__ == "__main__":
    main()
