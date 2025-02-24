"""
Module for processing teacher substitutions and absences from SkolaOnline.cz.

This module parses XML data and extracts information related to teacher absences
and substitutions. The extracted data can be exported in multiple formats,
including CSV, HTML, and PDF.

Features:
- Extracts and processes teacher absences.
- Extracts and processes substitution schedules.
- Generates structured reports in CSV, HTML, and PDF formats.
- Uses Jinja2 for templating and WeasyPrint for PDF generation.

Classes:
- `Suplovani`: Handles data extraction and file generation.

Dependencies:
- datetime
- xml.etree.ElementTree (ET)
- pandas
- weasyprint
- jinja2

Usage Example:
    suplovani = Suplovani("substitutions.xml")
    suplovani.export_path("/output")
    suplovani.generate("html")
"""

import pandas as pd
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

from .suplovani_base import SuplovaniBase

class SuplovaniUcitele(SuplovaniBase):
    """
    A class to process XML data from SkolaOnline.cz related to teacher absences
    and substitutions.

    This class provides methods for:
    - Extracting teacher, subject, classroom, and event mappings.
    - Extracting teacher absences and substitution records.
    - Generating CSV, HTML, and PDF reports from the extracted data.

    Attributes:
        xml_file (str): Path to the input XML file.
        template_folder (str): Folder containing Jinja2 templates.
        tree (ET.ElementTree): Parsed XML tree.
        root (ET.Element): Root element of the XML tree.
        date (datetime): Date extracted from the XML.
        _path (str): Output directory path for file exports.
    """

    def __init__(self, xml_file, template_folder="templates"):
        super().__init__(xml_file, template_folder)

        # Extract mappings
        self.class_mapping = self._extract_class_mappings()
        self.teacher_mapping = self._extract_teachers()
        self.room_mapping = self._extract_classrooms()
        self.event_room_mapping = self._extract_event_room_mappings()
        self.udalost_mapping = self._extract_event_group_mappings()
        self.absence_reason_mapping = self._extract_absence_reasons()

    def _extract_teachers(self):
        teachers = {}
        for teacher in self.root.findall(".//Ucitel") + self.root.findall(".//Ucitel2"):
            teacher_id = (
                teacher.find("OSOBA_ID").text
                if teacher.find("OSOBA_ID") is not None
                else ""
            )
            teacher_name = (
                f"{teacher.find('Prijmeni').text} {teacher.find('Jmeno').text}"
                if teacher.find("Prijmeni") is not None
                and teacher.find("Jmeno") is not None
                else ""
            )
            teacher_short = (
                teacher.find("Zkratka").text
                if teacher.find("Zkratka") is not None
                else ""
            )
            if teacher_id:
                teachers[teacher_id] = (teacher_name, teacher_short)
        return teachers

    def _extract_event_room_mappings(self):
        mappings = {}
        for event in self.root.findall(".//KalendarovaUdalostMistnost"):
            event_id = (
                event.find("UDALOST_ID").text
                if event.find("UDALOST_ID") is not None
                else ""
            )
            room_id = (
                event.find("MISTNOST_ID").text
                if event.find("MISTNOST_ID") is not None
                else ""
            )
            if event_id and room_id:
                if event_id not in mappings:
                    mappings[event_id] = []
                mappings[event_id].append(self.room_mapping.get(room_id, ""))
        return mappings

    def _extract_class_mappings(self):
        mappings = {}
        for group in self.root.findall(".//TridaSkupinaSeminar"):
            group_id = (
                group.find("SKUPINA_ID").text
                if group.find("SKUPINA_ID") is not None
                else ""
            )
            parent_id = (
                group.find("SKUPINA_ID_PARENT").text
                if group.find("SKUPINA_ID_PARENT") is not None
                else ""
            )
            name = group.find("Nazev").text if group.find("Nazev") is not None else ""
            if group_id:
                if parent_id and parent_id in mappings:
                    mappings[group_id] = f"{mappings[parent_id]} ({name})"
                else:
                    mappings[group_id] = name
        return mappings

    def _extract_event_group_mappings(self):
        return {
            event.find("UDALOST_ID").text: event.find("SKUPINA_ID").text
            for event in self.root.findall(".//UdalostStudijniSkupiny")
            if event.find("UDALOST_ID") is not None
        }

    def _extract_absence_reasons(self):
        return {
            absence.find("SUPL_DRUH_ABSENCE_ID").text: absence.find("Nazev").text
            for absence in self.root.findall(".//SuplovaniDruhAbsence")
        }

    def extract_absences(self):
        """
        Extracts teacher absences from the XML file.

        This method retrieves absence records, maps them to corresponding teachers,
        and associates them with predefined absence reasons.

        Returns:
            list[dict]: A list of dictionaries, each containing:
                - "Teacher": Name of the absent teacher.
                - "Reason": Reason for absence.

        Example Output:
            [
                {"Teacher": "John Doe", "Reason": "Sick Leave"},
                {"Teacher": "Jane Smith", "Reason": "Personal Leave"}
            ]
        """

        absences = []
        for absence in self.root.findall(".//AbsenceZdrojeVeDni"):
            reason_id = (
                absence.find("SUPL_DRUH_ABSENCE_ID").text
                if absence.find("SUPL_DRUH_ABSENCE_ID") is not None
                else ""
            )
            reason = self.absence_reason_mapping.get(reason_id, "Neznámý důvod")

            for teacher_absence in self.root.findall(".//AbsenceUcitele"):
                teacher_id = teacher_absence.find("OSOBA_ID").text
                teacher_name, _ = self.teacher_mapping.get(
                    teacher_id, ("Neznámý učitel", "")
                )

                absences.append({"Teacher": teacher_name, "Reason": reason})
        return absences

    def extract_substitutions(self):
        """
        Extracts teacher substitutions from the XML file.

        This method retrieves substitution records and maps them to their respective
        teachers, subjects, classrooms, and periods.

        Returns:
            list[dict]: A list of dictionaries, each containing:
                - "Teacher": Name of the teacher handling the substitution.
                - "Teacher_Abbreviation": Shortened name of the teacher.
                - "Subject": Subject of the class.
                - "Period": The period during which the class occurs.
                - "Room": Assigned classroom for the class.
                - "Class": The class or group affected.
                - "Resolution": How the substitution is handled.
                - "Note": Additional remarks.

        Example Output:
            [
                {
                    "Teacher": "John Doe",
                    "Teacher_Abbreviation": "JD",
                    "Subject": "Mathematics",
                    "Period": "2nd",
                    "Room": "101",
                    "Class": "3A",
                    "Resolution": "Substituted",
                    "Note": "Replaced by another teacher"
                }
            ]
        """

        substitutions = []
        for record in self.root.findall(".//VypisSuplovani"):
            teacher_id = (
                record.find("OSOBA_ID").text
                if record.find("OSOBA_ID") is not None
                else ""
            )
            subject_id = (
                record.find("REALIZACE_ID").text
                if record.find("REALIZACE_ID") is not None
                else ""
            )
            event_id = (
                record.find("UDALOST_ID").text
                if record.find("UDALOST_ID") is not None
                else ""
            )
            period_id = (
                record.find("OBDOBI_DNE_ID").text
                if record.find("OBDOBI_DNE_ID") is not None
                else ""
            )
            resolution = (
                record.find("ZpusobReseni").text
                if record.find("ZpusobReseni") is not None
                else ""
            )
            note = (
                record.find("Poznamka").text
                if record.find("Poznamka") is not None
                else ""
            )

            teacher_name, teacher_short = self.teacher_mapping.get(teacher_id, ("", ""))
            subject_name = self.subject_mapping.get(subject_id, "")
            period_name = self.period_mapping.get(period_id, "")
            class_name = self.class_mapping.get(
                self.udalost_mapping.get(event_id, ""), ""
            )

            room_list = self.event_room_mapping.get(event_id, [""])
            room_names = " , ".join(room_list)

            substitutions.append(
                {
                    "Teacher": teacher_name,
                    "Teacher_Abbreviation": teacher_short,
                    "Subject": subject_name,
                    "Period": period_name,
                    "Room": room_names,
                    "Class": class_name,
                    "Resolution": resolution,
                    "Note": note,
                }
            )
        return substitutions

    def generate(self, output_format):
        """
        Generates substitution reports in the specified format.

        Supported formats:
        - "csv": Generates CSV files for substitutions and absences.
        - "html": Generates an HTML report using Jinja2 templates.
        - "pdf": Converts the HTML report to a PDF using WeasyPrint.

        Args:
            output_format (str): Desired output format ("csv", "html", or "pdf").

        Returns:
            str: A message indicating the generated file type.

        Example Usage:
            suplovani.generate("csv")   # Generates CSV files
            suplovani.generate("html")  # Generates an HTML report
            suplovani.generate("pdf")   # Generates a PDF report

        Example Output:
            "CSV files generated."
            "HTML file generated."
            "PDF file generated."
        """

        absences = self.extract_absences()
        substitutions = self.extract_substitutions()

        timestamp = self.date.strftime('%Y_%m_%d')

        if output_format == "csv":
            pd.DataFrame(substitutions).to_csv(
                f"{self._path}/suplovani_{timestamp}.csv",
                index=False,
                sep=";",
            )
            pd.DataFrame(absences).to_csv(
                f"{self._path}/absences_{timestamp}.csv",
                index=False,
                sep=";",
            )
            return "CSV files generated."

        if output_format == "html":
            env = Environment(loader=FileSystemLoader(self.template_folder))
            template = env.get_template("teachers.html")
            html_content = template.render(
                date=self.date.strftime("%d.%m.%Y"),
                absences=absences,
                substitutions=substitutions,
            )

            with open(
                f"{self._path}/suplovani_{timestamp}.html",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(html_content)
            return "HTML file generated."

        if output_format == "pdf":
            HTML(
                filename=f"{self._path}/suplovani_{timestamp}.html"
            ).write_pdf(f"{self._path}/suplovani_{timestamp}.pdf")
            return "PDF file generated."

        return "Unsupported format!"
