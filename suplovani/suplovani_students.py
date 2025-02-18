import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

class SuplovaniZaci:
    def __init__(self, xml_file, template_folder="templates"):
        self.xml_file = xml_file
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        self.date = self._extract_date()
        self.template_folder = template_folder
        self._path = '.'

        # Extract mappings
        self.teacher_mapping = self._extract_teachers()
        self.subject_mapping = self._extract_subjects()
        self.room_mapping = self._extract_classrooms()
        self.period_mapping = self._extract_periods()
        self.class_mapping = self._extract_classes()
        self.group_mapping = self._extract_groups()
        self.event_group_mapping = self._extract_event_group_mappings()
        self.event_room_mapping = self._extract_event_room_mappings()
        self.event_teacher_mapping = self._extract_event_teacher_mappings()

    def export_path(self, path):
        self._path = path

    def _extract_date(self):
        date_element = self.root.find(".//Kalendar/Datum")
        return datetime.fromisoformat(date_element.text) if date_element is not None else None

    def _extract_teachers(self):
        return {
            teacher.find("OSOBA_ID").text: {
                "abbreviation": teacher.find("Zkratka").text,
                "name": f"{teacher.find('Jmeno').text} {teacher.find('Prijmeni').text}"
            }
            for teacher in self.root.findall(".//Ucitel2") + self.root.findall(".//Ucitel")
            if teacher.find("OSOBA_ID") is not None and teacher.find("Zkratka") is not None and teacher.find("Jmeno") is not None and teacher.find("Prijmeni") is not None
        }

    def _extract_subjects(self):
        return {
            subject.find("REALIZACE_ID").text: subject.find("Zkratka").text
            for subject in self.root.findall(".//Predmet")
            if subject.find("REALIZACE_ID") is not None and subject.find("Zkratka") is not None
        }

    def _extract_classrooms(self):
        return {
            room.find("MISTNOST_ID").text: room.find("Zkratka").text
            for room in self.root.findall(".//Mistnost")
            if room.find("MISTNOST_ID") is not None and room.find("Zkratka") is not None
        }

    def _extract_periods(self):
        return {
            period.find("OBDOBI_DNE_ID").text: period.find("Nazev").text
            for period in self.root.findall(".//VyucovaciHodinaOd")
            if period.find("OBDOBI_DNE_ID") is not None and period.find("Nazev") is not None
        }

    def _extract_classes(self):
        return {
            class_elem.find("SKUPINA_ID").text: class_elem.find("Nazev").text
            for class_elem in self.root.findall(".//Trida")
            if class_elem.find("SKUPINA_ID") is not None and class_elem.find("Nazev") is not None
        }

    def _extract_groups(self):
        return {
            group.find("SKUPINA_ID").text: {
                "class": self.class_mapping.get(group.find("SKUPINA_ID_PARENT").text, ""),
                "group": group.find("Nazev").text if group.find("Nazev") is not None else ""
            }
            for group in self.root.findall(".//TridaSkupinaSeminar")
            if group.find("SKUPINA_ID") is not None and group.find("SKUPINA_ID_PARENT") is not None
        }

    def _extract_event_group_mappings(self):
        return {
            event.find("UDALOST_ID").text: event.find("SKUPINA_ID").text
            for event in self.root.findall(".//UdalostStudijniSkupina")
            if event.find("UDALOST_ID") is not None and event.find("SKUPINA_ID") is not None
        }

    def _extract_event_room_mappings(self):
        return {
            event.find("UDALOST_ID").text: self.room_mapping.get(event.find("MISTNOST_ID").text, "")
            for event in self.root.findall(".//UdalostMistnost")
            if event.find("UDALOST_ID") is not None and event.find("MISTNOST_ID") is not None
        }

    def _extract_event_teacher_mappings(self):
        return {
            event.find("UDALOST_ID").text: event.find("OSOBA_ID").text
            for event in self.root.findall(".//UdalostOsoba")
            if event.find("UDALOST_ID") is not None and event.find("OSOBA_ID") is not None
        }

    def extract_substitutions(self):
        substitutions = []
        for record in self.root.findall(".//VypisSuplovaniZaka"):
            event_id = record.find("UDALOST_ID").text if record.find("UDALOST_ID") is not None else ""
            group_id = self.event_group_mapping.get(event_id, "")

            class_name = self.group_mapping.get(group_id, {}).get("class", "")
            group_name = self.group_mapping.get(group_id, {}).get("group", "")

            if group_name == class_name:
                group_name = ""

            period = self.period_mapping.get(record.find("OBDOBI_DNE_ID").text if record.find("OBDOBI_DNE_ID") is not None else "", "")
            subject = self.subject_mapping.get(record.find("REALIZACE_ID").text if record.find("REALIZACE_ID") is not None else "", "")
            room = self.event_room_mapping.get(event_id, "")

            osoba_id = self.event_teacher_mapping.get(event_id, "")
            teacher_info = self.teacher_mapping.get(osoba_id, {"abbreviation": "", "name": ""})

            resolution = record.find("ZpusobReseni").text if record.find("ZpusobReseni") is not None else ""
            note = record.find("Poznamka").text if record.find("Poznamka") is not None else ""

            substitutions.append({
                "Class": class_name,
                "Period": period,
                "Subject": subject,
                "Group": group_name,
                "Room": room,
                "Teacher": teacher_info["name"],
                "Teacher_Abbreviation": teacher_info["abbreviation"],
                "Resolution": resolution,
                "Note": note
            })
        return substitutions

    def generate(self, output_format):
        substitutions = self.extract_substitutions()

        if output_format == "csv":
            pd.DataFrame(substitutions).to_csv(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.csv", index=False, sep=";")
            return "CSV file generated."

        elif output_format == "html":
            env = Environment(loader=FileSystemLoader(self.template_folder))
            template = env.get_template("students.html")

            html_content = template.render(date=self.date.strftime('%d.%m.%Y'), substitutions=substitutions)

            with open(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return "HTML file generated."

        elif output_format == "pdf":
            HTML(filename=f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.html").write_pdf(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.pdf")
            return "PDF file generated."

        else:
            return "Unsupported format!"
