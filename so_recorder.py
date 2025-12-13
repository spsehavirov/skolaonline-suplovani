#!/usr/bin/env python
"""
Manual activity recorder for SkolaOnline that captures network requests.

Why:
    Use this when you want to perform actions manually in the browser but save
    the underlying HTTP calls (for later replay with requests/so_soap-style
    scripts).

What it does:
    - Logs into skolaonline.cz using .env credentials (SO_USER / SO_PASS).
    - Opens the target page (default: the substitution report filter).
    - Enables Chrome performance logging (Network.* events).
    - Lets you interact manually; press Enter in the terminal to stop.
    - Dumps captured network requests to a JSON file (default: network_log.json).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from colorama import Fore, init
from dotenv import find_dotenv, load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# URLs used during recording
LOGIN_URL = "https://www.skolaonline.cz/prihlaseni/?"
DEFAULT_START_URL = (
    "https://aplikace.skolaonline.cz/SOL/App/TiskoveSestavy/KTS004_Filtr.aspx"
    "?SestavaID=532a6c6e-f76a-46ab-9e5a-236b628da333"
    "&ReturnPage=/SOL/App/TiskoveSestavy/KTS003_SeznamSestav.aspx"
    "?SlozkaID=00000000-0000-0000-0000-000000000000&page=1"
)

init(autoreset=True)


def build_driver(headless: bool) -> webdriver.Chrome:
    """Create a Chrome driver with performance logging enabled."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    # Enable CDP network events
    driver.execute_cdp_cmd("Network.enable", {})
    return driver


def login(driver: webdriver.Chrome, username: str, password: str) -> None:
    """Log into SkolaOnline using the public login form."""
    driver.get(LOGIN_URL)
    driver.find_element(By.CSS_SELECTOR, "#JmenoUzivatele").send_keys(username)
    driver.find_element(By.CSS_SELECTOR, "#HesloUzivatele").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "#btnLogin").click()
    time.sleep(1.0)

    # Dismiss popups if present
    for sel in [
        "button#ctl00_ctl16_NeprecteneZpravyOtazka_btnPozdeji",
        "button#c-p-bn",
    ]:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).click()
            time.sleep(0.2)
        except NoSuchElementException:
            continue


def collect_requests(perf_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse Chrome performance logs into a concise list of network requests."""
    events: List[Dict[str, Any]] = []
    for entry in perf_logs:
        try:
            message = json.loads(entry["message"]).get("message", {})
        except (json.JSONDecodeError, KeyError):
            continue

        if message.get("method") != "Network.requestWillBeSent":
            continue

        params = message.get("params", {})
        request = params.get("request", {})
        url = request.get("url", "")
        if "skolaonline.cz" not in url.lower():
            continue  # Skip noise from other domains (analytics, etc.)

        events.append(
            {
                "timestamp": params.get("timestamp"),
                "method": request.get("method"),
                "url": url,
                "headers": request.get("headers"),
                "postData": request.get("postData"),
                "requestId": params.get("requestId"),
                "initiator": params.get("initiator"),
            }
        )
    return events


def save_log(events: List[Dict[str, Any]], output_path: Path) -> None:
    data = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "count": len(events),
        "requests": events,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as log_file:
        json.dump(data, log_file, ensure_ascii=False, indent=2)


def main() -> None:
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    username = os.getenv("SO_USER")
    password = os.getenv("SO_PASS")
    if not username or not password:
        raise SystemExit("Missing SO_USER or SO_PASS in .env")

    parser = argparse.ArgumentParser(description="Record manual activity network logs.")
    parser.add_argument(
        "--start-url",
        default=DEFAULT_START_URL,
        help="Page to open after login (perform your actions there).",
    )
    parser.add_argument(
        "--output",
        default="network_log.json",
        help="Where to save the captured requests (JSON).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome headless (manual clicks will be harder).",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    print(Fore.CYAN + "Starting Chrome with network logging...")
    driver = build_driver(headless=args.headless)
    try:
        login(driver, username, password)
        driver.get(args.start_url)
        print(Fore.GREEN + "Logged in. Perform your actions now.")
        print(
            Fore.YELLOW
            + f"When finished, return to this terminal and press Enter to save logs to {output_path}"
        )
        input()  # Wait for user to finish manual interactions

        logs = driver.get_log("performance")
        events = collect_requests(logs)
        save_log(events, output_path)
        print(Fore.GREEN + f"Saved {len(events)} requests to {output_path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
