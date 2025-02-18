import os
import csv
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from itertools import groupby
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

class Suplovani:
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
        self.event_room_mapping = self._extract_event_room_mappings()
        self.class_mapping = self._extract_class_mappings()
        self.udalost_mapping = self._extract_event_group_mappings()
        self.period_mapping = self._extract_periods()
        self.absence_reason_mapping = self._extract_absence_reasons()

    def export_path(self, path):
        self._path = path

    def _extract_date(self):
        date_element = self.root.find(".//Kalendar/Datum")
        return datetime.fromisoformat(date_element.text) if date_element is not None else None

    def _extract_teachers(self):
        teachers = {}
        for teacher in self.root.findall(".//Ucitel") + self.root.findall(".//Ucitel2"):
            teacher_id = teacher.find("OSOBA_ID").text if teacher.find("OSOBA_ID") is not None else ""
            teacher_name = f"{teacher.find('Prijmeni').text} {teacher.find('Jmeno').text}" if teacher.find("Prijmeni") is not None and teacher.find("Jmeno") is not None else ""
            teacher_short = teacher.find("Zkratka").text if teacher.find("Zkratka") is not None else ""
            if teacher_id:
                teachers[teacher_id] = (teacher_name, teacher_short)
        return teachers

    def _extract_subjects(self):
        return {subject.find("REALIZACE_ID").text: subject.find("Zkratka").text
                for subject in self.root.findall(".//Predmet") if subject.find("REALIZACE_ID") is not None}

    def _extract_classrooms(self):
        return {room.find("MISTNOST_ID").text: room.find("Zkratka").text
                for room in self.root.findall(".//Mistnost") if room.find("MISTNOST_ID") is not None}

    def _extract_event_room_mappings(self):
        mappings = {}
        for event in self.root.findall(".//KalendarovaUdalostMistnost"):
            event_id = event.find("UDALOST_ID").text if event.find("UDALOST_ID") is not None else ""
            room_id = event.find("MISTNOST_ID").text if event.find("MISTNOST_ID") is not None else ""
            if event_id and room_id:
                if event_id not in mappings:
                    mappings[event_id] = []
                mappings[event_id].append(self.room_mapping.get(room_id, ""))
        return mappings

    def _extract_class_mappings(self):
        mappings = {}
        for group in self.root.findall(".//TridaSkupinaSeminar"):
            group_id = group.find("SKUPINA_ID").text if group.find("SKUPINA_ID") is not None else ""
            parent_id = group.find("SKUPINA_ID_PARENT").text if group.find("SKUPINA_ID_PARENT") is not None else ""
            name = group.find("Nazev").text if group.find("Nazev") is not None else ""
            if group_id:
                if parent_id and parent_id in mappings:
                    mappings[group_id] = f"{mappings[parent_id]} ({name})"
                else:
                    mappings[group_id] = name
        return mappings

    def _extract_event_group_mappings(self):
        return {event.find("UDALOST_ID").text: event.find("SKUPINA_ID").text
                for event in self.root.findall(".//UdalostStudijniSkupiny") if event.find("UDALOST_ID") is not None}

    def _extract_periods(self):
        return {period.find("OBDOBI_DNE_ID").text: period.find("Nazev").text
                for period in self.root.findall(".//VyucovaciHodinaOd") if period.find("OBDOBI_DNE_ID") is not None}

    def _extract_absence_reasons(self):
        return {absence.find("SUPL_DRUH_ABSENCE_ID").text: absence.find("Nazev").text
                for absence in self.root.findall(".//SuplovaniDruhAbsence")}

    def extract_absences(self):
        absences = []
        for absence in self.root.findall(".//AbsenceZdrojeVeDni"):
            reason_id = absence.find("SUPL_DRUH_ABSENCE_ID").text if absence.find("SUPL_DRUH_ABSENCE_ID") is not None else ""
            reason = self.absence_reason_mapping.get(reason_id, "Neznámý důvod")

            for teacher_absence in self.root.findall(".//AbsenceUcitele"):
                teacher_id = teacher_absence.find("OSOBA_ID").text
                teacher_name, _ = self.teacher_mapping.get(teacher_id, ("Neznámý učitel", ""))

                absences.append({
                    "Teacher": teacher_name,
                    "Reason": reason
                })
        return absences

    def extract_substitutions(self):
        substitutions = []
        for record in self.root.findall(".//VypisSuplovani"):
            teacher_id = record.find("OSOBA_ID").text if record.find("OSOBA_ID") is not None else ""
            subject_id = record.find("REALIZACE_ID").text if record.find("REALIZACE_ID") is not None else ""
            event_id = record.find("UDALOST_ID").text if record.find("UDALOST_ID") is not None else ""
            period_id = record.find("OBDOBI_DNE_ID").text if record.find("OBDOBI_DNE_ID") is not None else ""
            resolution = record.find("ZpusobReseni").text if record.find("ZpusobReseni") is not None else ""
            note = record.find("Poznamka").text if record.find("Poznamka") is not None else ""

            teacher_name, teacher_short = self.teacher_mapping.get(teacher_id, ("", ""))
            subject_name = self.subject_mapping.get(subject_id, "")
            period_name = self.period_mapping.get(period_id, "")
            class_name = self.class_mapping.get(self.udalost_mapping.get(event_id, ""), "")

            room_list = self.event_room_mapping.get(event_id, [""])
            room_names = " , ".join(room_list)

            substitutions.append({
                "Teacher": teacher_name,
                "Teacher_Abbreviation": teacher_short,
                "Subject": subject_name,
                "Period": period_name,
                "Room": room_names,
                "Class": class_name,
                "Resolution": resolution,
                "Note": note
            })
        return substitutions

    def generate(self, output_format):
        absences = self.extract_absences()
        substitutions = self.extract_substitutions()

        if output_format == "csv":
            pd.DataFrame(substitutions).to_csv(f"{self._path}/suplovani_{self.date.strftime('%Y_%m_%d')}.csv", index=False, sep=";")
            pd.DataFrame(absences).to_csv(f"{self._path}/absences_{self.date.strftime('%Y_%m_%d')}.csv", index=False, sep=";")
            return "CSV files generated."

        elif output_format == "html":
            env = Environment(loader=FileSystemLoader(self.template_folder))
            template = env.get_template("teachers.html")
            html_content = template.render(date=self.date.strftime('%d.%m.%Y'), absences=absences, substitutions=substitutions)

            with open(f"{self._path}/suplovani_{self.date.strftime('%Y_%m_%d')}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return "HTML file generated."

        elif output_format == "pdf":
            HTML(filename=f"{self._path}/suplovani_{self.date.strftime('%Y_%m_%d')}.html").write_pdf(f"{self._path}/suplovani_{self.date.strftime('%Y_%m_%d')}.pdf")
            return "PDF file generated."

        else:
            return "Unsupported format!"
