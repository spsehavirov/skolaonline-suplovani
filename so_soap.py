#!/usr/bin/env python3
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
# Bootstrap must precede third-party imports to select the installed environment.
# pylint: disable=wrong-import-order

from __future__ import annotations

from project_env import run_in_project_venv

if __name__ == "__main__":
    run_in_project_venv(__file__)

import argparse
import os
from datetime import datetime
from typing import Optional, Tuple
from xml.etree.ElementTree import ParseError

import requests
import yaml
from bs4 import BeautifulSoup
from colorama import Fore, init
from dotenv import find_dotenv, load_dotenv
from requests_toolbelt import MultipartEncoder
from supl.filters import add_filter_arguments, build_policy, parse_date
from supl.jobs import prepare_download, publish_xml

# Constants used by the SkolaOnline form flow
LOGIN_URL = "https://aplikace.skolaonline.cz/SOL/Prihlaseni.aspx"
FILTER_URL = (
    "https://aplikace.skolaonline.cz/SOL/App/TiskoveSestavy/KTS004_Filtr.aspx"
    "?SestavaID="
        "84ad1259-cfd8-417a-ab4e-7287846a6873"
    "&ReturnPage="
        "/SOL/App/TiskoveSestavy/KTS003_SeznamSestav.aspx"
    "?SlozkaID="
        "00000000-0000-0000-0000-000000000000"
    "&page=1"
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
    return datetime.combine(parse_date(date_str), datetime.min.time())


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


def _save_xml(content: bytes, date_obj: datetime, config: dict, policy=None) -> str:
    """Persist the downloaded XML into the configured watch folder."""
    report_date = date_obj.date()
    if policy is None:
        policy = build_policy(config["settings"], report_date)
    return publish_xml(content, report_date, config, policy)


def build_parser():
    """Describe the shared download and per-report filter arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help='Date to download (e.g. "25.02.2025").')
    add_filter_arguments(parser)
    return parser


def main():
    """Download substitution XML without changing saved rules or .env."""
    parser = build_parser()
    args = parser.parse_args()
    custom_date = args.date or os.getenv("DATE_TO_PROCESS")
    try:
        config, report_date, policy = prepare_download(CONFIG, custom_date, args)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    date_obj = datetime.combine(report_date, datetime.min.time())
    date_for_form = report_date.strftime("%d.%m.%Y")

    try:
        _ensure_credentials()
        with requests.Session() as session:
            _login(session)
            xml_content = _download_xml(session, date_for_form)
        saved_path = _save_xml(xml_content, date_obj, config, policy)
        print(Fore.GREEN + f"XML file saved to: {saved_path}")
    except (requests.RequestException, DownloadError, ValueError, OSError, ParseError) as exc:
        print(Fore.RED + f"Download failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
