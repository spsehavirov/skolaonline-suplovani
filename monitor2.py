import os
import time
import yaml
import xml.etree.ElementTree as ET
from suplovani import Suplovani
from suplovani_students import SuplovaniZaci

# Load configuration from YAML file
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

WATCH_FOLDER = config["settings"]["watch_folder"]
OUTPUT_FOLDER = config["settings"]["output_folder"]
CHECK_INTERVAL = config["settings"]["check_interval"]

def detect_suplovani_type(xml_file):
    """
        Detects if the XML file is for students or teachers.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # If it contains <UdalostStudijniSkupiny>, it's for students
    if root.find(".//VypisSuplovaniZaka") is not None:
        return "students"

    # If it contains <AbsenceUcitele> elements, it's for teachers
    elif root.find(".//VypisSuplovani") is not None:
        return "teachers"

    # Default to teachers if unclear
    return None

def process_suplovani(xml_file):
    """
        Detect the type and process the XML file accordingly.
    """
    suplovani_type = detect_suplovani_type(xml_file)

    if suplovani_type == None:
        print("📂 Unknown XML, skipping ...")
        return

    if suplovani_type == "teachers":
        print("📂 Detected TEACHERS' suplování XML")
        supl = Suplovani(xml_file)
    else:
        print("📂 Detected STUDENTS' suplování XML")
        supl = SuplovaniZaci(xml_file)

    supl.export_path(OUTPUT_FOLDER)

    print(supl.generate("csv"))  # Generates CSV
    print(supl.generate("html"))  # Generates HTML
    print(supl.generate("pdf"))  # Converts HTML to PDF

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
        monitor_folder()

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")
