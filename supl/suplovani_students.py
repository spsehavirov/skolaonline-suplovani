"""
Module for processing student substitution schedules from SkolaOnline.cz.

This module extracts and processes XML data to generate substitution reports
in multiple formats, including CSV, HTML, PDF, and PNG. It handles event
grouping, teacher, subject, and classroom mappings, and refines substitution
records to eliminate duplicate or conflicting information.

Features:
- Extracts relevant substitution data from XML exported by SkolaOnline.cz.
- Maps teachers, subjects, classrooms, and periods to their respective IDs.
- Groups events logically to resolve cancellations and substitutions.
- Generates structured output in various formats:
  - CSV: Machine-readable tabular data.
  - HTML: Styled report using Jinja2 templates.
  - PDF: Printable version via WeasyPrint.
  - PNG: Image snapshots of the PDF report using pymupdf.
- Supports dynamic color coding for headers based on the day of the week.

Classes:
- `SuplovaniZaci`: Main class handling extraction, processing, and export.

Dependencies:
- datetime
- xml.etree.ElementTree (ET)
- pandas
- pymupdf
- weasyprint
- jinja2

Usage Example:
    suplovani = SuplovaniZaci("substitutions.xml")
    suplovani.export_path("/output")
    suplovani.generate("html")
"""

# pylint: disable=R0914
# pylint: disable=R0902
# pylint: disable=R0801

import os
import glob
from datetime import datetime

import pymupdf
import pandas as pd
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

from .suplovani_base import SuplovaniBase
from .settings import Settings
from .hours import SchoolSchedule


class SuplovaniZaci(SuplovaniBase):
    """
    Process the XML output generated by SkolaOnline.cz and extract the data
    (quick and dirty) into the CSV, HTML, PDF and PNG.

    The current version supports grouping of events (in event of class
    cancellation and substitution happening at the same time)
    """

    def __init__(self, xml_file, settings: Settings, template_folder="templates"):
        super().__init__(xml_file, settings, template_folder)

        # Extract mappings
        self.teacher_mapping = self._extract_teachers()
        self.class_mapping = self._extract_classes()
        self.group_mapping = self._extract_groups()
        self.event_group_mapping = self._extract_event_group_mappings()
        self.event_room_mapping = self._extract_event_room_mappings()
        self.event_teacher_mapping = self._extract_event_teacher_mappings()
        self.absence_reason_mapping = self._extract_absence_reasons()

    def _extract_teachers(self):
        return {
            teacher.find("OSOBA_ID").text: {
                "abbreviation": teacher.find("Zkratka").text,
                "name": f"{teacher.find('Jmeno').text} {teacher.find('Prijmeni').text}",
            }
            for teacher in self.root.findall(".//Ucitel2")
            + self.root.findall(".//Ucitel")
            if teacher.find("OSOBA_ID") is not None
            and teacher.find("Zkratka") is not None
            and teacher.find("Jmeno") is not None
            and teacher.find("Prijmeni") is not None
        }

    def _extract_classes(self):
        return {
            class_elem.find("SKUPINA_ID").text: class_elem.find("Nazev").text
            for class_elem in self.root.findall(".//Trida")
            if class_elem.find("SKUPINA_ID") is not None
            and class_elem.find("Nazev") is not None
        }

    def _extract_groups(self):
        return {
            group.find("SKUPINA_ID").text: {
                "class": self.class_mapping.get(
                    group.find("SKUPINA_ID_PARENT").text, ""
                ),
                "group": (
                    group.find("Nazev").text if group.find("Nazev") is not None else ""
                ),
            }
            for group in self.root.findall(".//TridaSkupinaSeminar")
            if group.find("SKUPINA_ID") is not None
            and group.find("SKUPINA_ID_PARENT") is not None
        }

    def _extract_event_group_mappings(self):
        return {
            event.find("UDALOST_ID").text: event.find("SKUPINA_ID").text
            for event in self.root.findall(".//UdalostStudijniSkupina")
            if event.find("UDALOST_ID") is not None
            and event.find("SKUPINA_ID") is not None
        }

    def _extract_event_room_mappings(self):
        mappings = {}
        for event in self.root.findall(".//UdalostMistnost"):
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

    def _extract_event_teacher_mappings(self):
        teachers_by_event = {}  # Používáme běžný slovník

        for event in self.root.findall(".//UdalostOsoba"):
            udalost_id = event.find("UDALOST_ID")
            osoba_id = event.find("OSOBA_ID")

            if udalost_id is not None and osoba_id is not None:
                uid = udalost_id.text
                oid = osoba_id.text

                if uid not in teachers_by_event:
                    teachers_by_event[uid] = []  # Inicializujeme prázdný seznam
                teachers_by_event[uid].append(oid)  # Přidáme osobu k události
        return teachers_by_event

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
        schedule = SchoolSchedule()
        for absence in self.root.findall(".//AbsenceZdrojeVeDni"):
            reason_id = super().get(absence, "SUPL_DRUH_ABSENCE_ID")
            reason = self.absence_reason_mapping.get(reason_id, "Neznámý důvod")

            udalost_id = super().get(absence, "UDALOST_ID", None)

            for teacher_absence in self.root.findall(".//AbsenceUcitele"):
                tau = super().get(teacher_absence, "UDALOST_ID", False)
                if udalost_id != tau:
                    # skip unrelated teacher (another event)
                    continue

                teacher_id = super().get(teacher_absence, "OSOBA_ID", None)
                if not teacher_id:
                    print(f"Missing Teacher ID, skipping {teacher_absence}")
                    continue

                teacher_info = self.teacher_mapping.get(
                    teacher_id, {"name": "Neznámý učitel"}
                )  # Ensure it's a dict

                # Skip the assistents and other personal from the absences
                if teacher_info.get("abbreviation", None).upper() in [
                    "KOP",
                    "HRN",
                    "HEI",
                ]:
                    continue

                od = super().get(absence, "Od")
                do = super().get(absence, "Do")

                # Using ISO 8601 datetime strings
                _, period_range = schedule.from_iso(od, do)
                # print(f"Detected Periods: {periods}, Range: {period_range}")

                absences.append(
                    {
                        "Teacher": teacher_info.get("name", "Neznámý učitel"),
                        "Reason": reason,
                        "From": datetime.fromisoformat(od).strftime("%H:%M"),
                        "To": datetime.fromisoformat(do).strftime("%H:%M"),
                        "Periods": period_range,
                    }
                )
        return absences

    def extract_substitutions(self):
        """Get the main data structure out of the XML for further processing"""
        substitutions = []
        for record in self.root.findall(".//VypisSuplovaniZaka"):
            event_id = super().get(record, "UDALOST_ID")
            group_id = self.event_group_mapping.get(event_id, "")

            class_name = self.group_mapping.get(group_id, {}).get("class", "")
            group_name = self.group_mapping.get(group_id, {}).get("group", "")

            if group_name == class_name:
                group_name = ""

            period = self.period_mapping.get(super().get(record, "OBDOBI_DNE_ID"), "")

            # Workaround for the way the SO hangles the period ranges
            od = super().get(record, "CasOd")
            do = super().get(record, "CasDo")

            schedule = SchoolSchedule()
            _, period_range = schedule.from_iso(od, do)

            if period != period_range:
                period = period_range

            subject = self.subject_mapping.get(super().get(record, "REALIZACE_ID"), "")
            rooms = self.event_room_mapping.get(event_id, [""])
            room = ", ".join(rooms)

            osoba_ids = self.event_teacher_mapping.get(event_id, [])
            # Fetch list of teacher IDs
            teachers_info = [
                self.teacher_mapping.get(oid, {"abbreviation": "", "name": ""})
                for oid in osoba_ids
            ]
            teacher_names = ", ".join(
                [t["name"] for t in teachers_info if t["name"]]
            )  # Combine names
            teacher_abbreviations = ", ".join(
                [t["abbreviation"] for t in teachers_info if t["abbreviation"]]
            )  # Combine abbreviations

            resolution = super().get(record, "ZpusobReseni")
            note = super().get(record, "Poznamka")

            write = True
            if (
                self.classes_to_include() is not None
                and len(self.classes_to_include()) > 0
            ):
                write = class_name in self.classes_to_include()
            elif (
                self.classes_to_exclude() is not None
                and len(self.classes_to_exclude()) > 0
            ):
                write = class_name not in self.classes_to_exclude()

            if write:
                substitutions.append(
                    {
                        "Class": class_name,
                        "Period": period,
                        "Subject": subject,
                        "Group": group_name,
                        "Room": room,
                        "Teacher": teacher_names,
                        "Teacher_Abbreviation": teacher_abbreviations,
                        "Resolution": resolution,
                        "Note": note,
                    }
                )
        return substitutions

    def extract_final_substitutions(self, records):
        """
        Iteratively processes a list of substitution records (each a dict with keys "Class",
        "Group", "Period", "Resolution", "Note", "Subject", etc.) and returns a deduplicated
        list where for each (Class, Period, Group) key any cancellation record ("odpadá")
        is omitted if a substitution record exists.
        """

        final_records = {}

        for rec in records:
            # Define the key. If the class is divided into groups, make sure "Group" is not empty.
            key = (rec.get("Class", ""), rec.get("Period", ""), rec.get("Group", ""))
            current_is_sub = rec.get("Resolution", "").strip() != "odpadá"

            if key not in final_records:
                # Nothing stored yet: simply store this record.
                final_records[key] = rec
            else:
                existing = final_records[key]
                existing_is_sub = existing.get("Resolution", "").strip() != "odpadá"

                # Rule: substitution should override a cancellation.
                if current_is_sub and not existing_is_sub:
                    # If the new substitution record has no note, add one based
                    # on the cancelled record.
                    if not rec.get("Note", "").strip():
                        subject = existing.get("Subject", "").strip()
                        if subject:
                            rec["Note"] = f"za {subject}"
                    final_records[key] = rec

                # If both are substitutions, decide on a tie-breaker.
                elif current_is_sub and existing_is_sub:
                    pass  # or implement additional merging logic if needed
                # If both are cancellations, we simply keep the existing record.
                else:
                    pass  # Otherwise, simply keep the existing record.

        # Return the deduplicated records as a list.
        return list(final_records.values())

    def extract_final_substitutions2(self, records):
        """
        Processes the list of substitution records by grouping them based on (Class, Period).
        If a general cancellation exists (Group is empty and Resolution == "odpadá"),
        it updates substitution records with a missing Note by adding "za [Subject]".
        If any substitution exists, the general cancellation is omitted.
        """

        def group_records(records):
            grouped = {}
            for rec in records:
                key = (rec.get("Class", ""), rec.get("Period", ""))
                grouped.setdefault(key, []).append(rec)
            return grouped

        def classify_records(recs):
            """Separate general cancellation from subgroup records."""
            general_cancel = None
            subgroup_records = []
            for r in recs:
                group, resolution = (
                    r.get("Group", "").strip(),
                    r.get("Resolution", "").strip(),
                )
                if group == "" and resolution == "odpadá":
                    general_cancel = r
                else:
                    subgroup_records.append(r)
            return general_cancel, subgroup_records

        def update_notes(subs, general_cancel):
            """Update substitution records with missing notes based on general cancellation."""
            if general_cancel:
                cancellation_subject = general_cancel.get("Subject", "").strip()
                for r in subs:
                    if not r.get("Note", "").strip() and cancellation_subject:
                        r["Note"] = f"za {cancellation_subject}"

        final_list = []
        grouped_records = group_records(records)

        for _, recs in grouped_records.items():
            general_cancel, subgroup_records = classify_records(recs)
            substitutions = [
                r
                for r in subgroup_records
                if r.get("Resolution", "").strip() != "odpadá"
            ]

            if substitutions:
                update_notes(substitutions, general_cancel)
                final_list.extend(substitutions)
            elif general_cancel:
                final_list.append(general_cancel)
            else:
                final_list.extend(recs)

        return final_list

    def _export_filename_prefix(self):
        day_of_week = self.date.isoweekday()

        day_names = {
            1: "po",
            2: "ut",
            3: "st",
            4: "ct",
            5: "pa",
            6: "so",
            7: "ne",
        }

        return (
            f"supl_{self.date.strftime('%y-%m-%d')}_{day_names.get(day_of_week, "x")}"
        )

    def _cleanup(self, extension):
        pattern = os.path.join(
            self._path, f"{self._export_filename_prefix()}*.{extension}"
        )
        for file_to_delete in glob.glob(pattern):
            try:
                os.remove(file_to_delete)
                print(f"Deleted file: {file_to_delete}")
            except OSError as e:
                print(f"Error deleting file {file_to_delete}: {e}")

    def generate(self, output_format):
        """
        Generate the output to a specified format.

        Currently the function expect the order for some type:
            -> HTML -> PDF -> PNG (subsequent file generation)
        """
        absences = self.extract_absences()
        raw_substitutions = self.extract_substitutions()
        substitutions = self.extract_final_substitutions2(raw_substitutions)

        self._cleanup(output_format)  # CLEANUP the previous versions

        if output_format == "csv":
            export_to = f"{self._path}/{self._export_filename_prefix()}.csv"
            pd.DataFrame(raw_substitutions).to_csv(export_to, index=False, sep=";")
            return "CSV file generated."

        if output_format == "html":
            export_to = f"{self._path}/{self._export_filename_prefix()}.html"

            env = Environment(loader=FileSystemLoader(self.template_folder))
            template = env.get_template("students.html")

            header_colors = {
                1: "#4f34ca",  # Monday
                2: "#c038cf",  # Tuesday
                3: "#FB536A",  # Wednesday
                4: "#e56e2e",  # Thursday
                5: "#eaa72f",  # Friday
                6: "#a0ea48",  # Saturday
                7: "#19cc59",  # Sunday
            }

            czech_day_names = {
                1: "Pondělí",
                2: "Úterý",
                3: "Středa",
                4: "Čtvrtek",
                5: "Pátek",
                6: "Sobota",
                7: "Neděle",
            }

            # Get values using dictionary lookup with a fallback
            day_of_week = self.date.isoweekday()
            header_color = header_colors.get(day_of_week, "#0984e3")
            localized_day = czech_day_names.get(day_of_week, "Neznámý den")

            html_content = template.render(
                date=self.date.strftime("%d.%m.%Y"),
                substitutions=substitutions,
                header_color=header_color,
                absences=absences,
                day=localized_day,
            )

            with open(export_to, "w", encoding="utf-8") as f:
                f.write(html_content)
            return "HTML file generated."

        if output_format == "pdf":
            import_from = f"{self._path}/{self._export_filename_prefix()}.html"
            export_to = f"{self._path}/{self._export_filename_prefix()}.pdf"
            HTML(filename=import_from).write_pdf(export_to)
            return "PDF file generated."

        if output_format == "png":
            pdf = f"{self._path}/{self._export_filename_prefix()}.pdf"
            export_prefix = f"{self._path}/{self._export_filename_prefix()}"

            doc = pymupdf.open(pdf)
            desired_dpi = 600
            zoom = desired_dpi / 72  # 72 DPI is the default resolution
            mat = pymupdf.Matrix(
                zoom, zoom
            )  # Create a transformation matrix for scaling
            # Loop through each page and save as a PNG image
            for page_number in range(doc.page_count):
                page = doc[page_number]
                # Render the page to an image (pixmap)
                pix = page.get_pixmap(matrix=mat)
                # Define output filename
                output_filename = f"{export_prefix}_{page_number + 1}.png"
                # Save the image
                pix.save(output_filename)
                print(f"Saved {output_filename}")
            return "Png(s) generated."

        return "Unsupported format!"
