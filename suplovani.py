import os
import time
import yaml
import shutil
import xml.etree.ElementTree as ET
from suplovani import Suplovani, SuplovaniZaci

# Load configuration from YAML file
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

WATCH_FOLDER = config["settings"]["watch_folder"]
OUTPUT_FOLDER = config["settings"]["output_folder"]
CHECK_INTERVAL = config["settings"]["check_interval"]
PROCESSED_FOLDER = os.path.join(WATCH_FOLDER, "processed")

# Ensure processed folder exists
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def detect_suplovani_type(xml_file):
    """
        Detects if the XML file is for students or teachers.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    if root.find(".//VypisSuplovaniZaka") is not None:
        return "students"
    elif root.find(".//VypisSuplovani") is not None:
        return "teachers"
    return None

def process_suplovani(xml_file):
    """
        Detect the type and process the XML file accordingly.
    """
    suplovani_type = detect_suplovani_type(xml_file)

    if suplovani_type is None:
        print("📂 Unknown XML, skipping ...")
        return

    if suplovani_type == "teachers":
        print("📂 Detected TEACHERS' suplování XML")
        supl = Suplovani(xml_file)
    else:
        print("📂 Detected STUDENTS' suplování XML")
        supl = SuplovaniZaci(xml_file)

    supl.export_path(OUTPUT_FOLDER)
    print(supl.generate("csv"))
    print(supl.generate("html"))
    print(supl.generate("pdf"))

    # Move processed file
    shutil.move(xml_file, os.path.join(PROCESSED_FOLDER, os.path.basename(xml_file)))
    print(f"📂 Moved {xml_file} to {PROCESSED_FOLDER}")

def process_existing_files():
    """
        Process all existing XML files in the watch folder on startup.
    """
    print("🔄 Processing existing XML files...")
    for file in os.listdir(WATCH_FOLDER):
        file_path = os.path.join(WATCH_FOLDER, file)
        if file.endswith(".xml"):
            print(f"📂 Processing existing XML: {file}")
            process_suplovani(file_path)

def monitor_folder():
    """
        Monitor a folder for new XML files and process them.
    """
    processed_files = set(os.listdir(WATCH_FOLDER))

    while True:
        time.sleep(CHECK_INTERVAL)
        current_files = set(os.listdir(WATCH_FOLDER))
        new_files = current_files - processed_files

        for file in new_files:
            if file.endswith(".xml"):
                file_path = os.path.join(WATCH_FOLDER, file)
                print(f"📂 New XML detected: {file}")
                process_suplovani(file_path)

        processed_files = current_files

if __name__ == "__main__":
    try:
        print(f"🔍 Monitoring folder: {WATCH_FOLDER}")
        process_existing_files()
        monitor_folder()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")
