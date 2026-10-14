#!/usr/bin/env python3
"""
Automated XML Processing for Teacher and Student Substitutions.

This script monitors a specified folder for XML files containing substitution
data from SkolaOnline.cz. It detects whether the XML file contains data for
students or teachers and processes it accordingly by generating reports
in CSV, HTML, PDF, and PNG formats.

Features:
- Watches a folder for new XML files and processes them automatically.
- Supports both teacher and student substitution formats.
- Generates structured output in multiple formats.
- Moves processed XML files to a dedicated folder.

Configuration:
- Settings (e.g., watch folder, output folder, check interval) are loaded from `config.yaml`.

Functions:
- `detect_suplovani_type(xml_file)`: Identifies whether the XML is for students or teachers.
- `process_suplovani(xml_file)`: Processes the XML file and generates reports.
- `process_existing_files()`: Processes any XML files already in the watch folder at startup.
- `monitor_folder()`: Continuously monitors the folder for new XML files.

Dependencies:
- os
- time
- shutil
- yaml
- xml.etree.ElementTree (ET)
- suplovani (custom module)

Usage:
    $ python monitor.py
    Press Ctrl+C to stop monitoring.

Example config.yaml:
    settings:
      watch_folder: "./watch"
      output_folder: "./output"
      check_interval: 10
      output:
        - csv
        - html
        - pdf
        - png
      exclude/include:
        - 1A
"""

# pylint: disable=R0801

from project_env import run_in_project_venv

if __name__ == "__main__":
    run_in_project_venv(__file__)

import argparse
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from colorama import init, Fore
from supl import SuplovaniUcitele, SuplovaniZaci, Settings
from supl.jobs import archive_xml, settings_for_xml, sidecar_path

# Load configuration from YAML file
config = Settings(config_path="config.yaml", cache_ttl=10)

# This config options require you to restart the monitor!
WATCH_FOLDER = config.get("watch_folder", "./watch")
CHECK_INTERVAL = config.get("check_interval", 2)
PROCESSED_FOLDER = os.path.join(WATCH_FOLDER, "processed")

# Enable colored terminal output
init(autoreset=True)


def detect_suplovani_type(xml_file):
    """
    Detects if the XML file is for students or teachers.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    if root.find(".//VypisSuplovaniZaka") is not None:
        return "students"
    if root.find(".//VypisSuplovani") is not None:
        return "teachers"
    return None


def process_suplovani(xml_file):
    """Keep failed inputs available for correction and let other jobs continue."""
    try:
        return _process_suplovani(xml_file)
    except Exception as exc:  # The monitor is the boundary for independent jobs.
        print(Fore.RED + f"Processing failed for {xml_file}: {exc}")
        return False


def _process_suplovani(xml_file):
    """
    Detect the type and process the XML file accordingly.
    """
    suplovani_type = detect_suplovani_type(xml_file)

    if suplovani_type is None:
        print(Fore.RED + "📂 Unknown XML, skipping ...")
        return False

    job_settings = settings_for_xml(xml_file, config)

    if suplovani_type == "teachers":
        print(Fore.LIGHTGREEN_EX + "📂 Detected 'TEACHERS' suplování XML")
        supl = SuplovaniUcitele(xml_file, job_settings)
    else:
        print(Fore.GREEN + "📂 Detected 'STUDENTS' suplování XML")
        supl = SuplovaniZaci(xml_file, job_settings)

    output_folder = job_settings.get("output_folder", "./outputs")
    os.makedirs(output_folder, exist_ok=True)
    supl.export_path(output_folder)

    for f in job_settings.get("output", ["csv", "html", "pdf", "png"]):
        print(Fore.YELLOW + supl.generate(f))

    # Move processed file
    destination = archive_xml(xml_file, PROCESSED_FOLDER)
    print(Fore.MAGENTA + f"📂 Archived {xml_file} to {destination}")
    return True


def process_existing_files():
    """
    Process all existing XML files in the watch folder on startup.
    """
    print(Fore.YELLOW + "🔄 Processing existing XML files...")
    for file in os.listdir(WATCH_FOLDER):
        file_path = os.path.join(WATCH_FOLDER, file)
        if file.endswith(".xml"):
            print(Fore.CYAN + f"📂 Processing existing XML: {file}")
            process_suplovani(file_path)


def monitor_folder():
    """
    Monitor a folder for new XML files and process them.
    """
    attempted = {}
    while True:
        time.sleep(CHECK_INTERVAL)
        current = {}
        for xml_path in Path(WATCH_FOLDER).glob("*.xml"):
            paths = (xml_path, sidecar_path(xml_path), Path(config.config_path))
            try:
                signature = tuple((path.stat().st_mtime_ns, path.stat().st_size)
                                  if path.exists() else None for path in paths)
            except FileNotFoundError:
                continue
            current[xml_path] = signature
            if attempted.get(xml_path) != signature:
                print(Fore.GREEN + f"📂 New or updated XML detected: {xml_path.name}")
                process_suplovani(xml_path)
        attempted = current


def build_parser():
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Monitor a folder for SkolaOnline XML substitutions and generate outputs."
        )
    )
    return parser


if __name__ == "__main__":
    try:
        build_parser().parse_known_args()
        os.makedirs(WATCH_FOLDER, exist_ok=True)
        print(Fore.MAGENTA + f"🔍 Monitoring folder: {WATCH_FOLDER}")
        process_existing_files()
        monitor_folder()
    except KeyboardInterrupt:
        print(Fore.BLUE + "\n🛑 Monitoring stopped by user.")
