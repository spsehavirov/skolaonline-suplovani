import os
import csv
import pymupdf
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
            current_is_sub = (rec.get("Resolution", "").strip() != "odpadá")

            if key not in final_records:
                # Nothing stored yet: simply store this record.
                final_records[key] = rec
            else:
                existing = final_records[key]
                existing_is_sub = (existing.get("Resolution", "").strip() != "odpadá")

                # Rule: substitution should override a cancellation.
                if current_is_sub and not existing_is_sub:
                    # If the new substitution record has no note, add one based on the cancelled record.
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
                    pass # Otherwise, simply keep the existing record.

        # Return the deduplicated records as a list.
        return list(final_records.values())

    def extract_final_substitutions2(self, records):
        """
        Processes the list of substitution records (each a dict with keys "Class",
        "Period", "Group", "Resolution", "Note", "Subject", etc.) by grouping them based
        on (Class, Period). When a general cancellation (Group is empty and Resolution == "odpadá")
        exists for that slot, then for each record that is for a specific group (non-empty Group)
        and is a substitution (Resolution != "odpadá"), if its Note is empty, add a note "za [Subject]"
        where [Subject] is taken from the general cancellation.

        Finally, if any substitution record exists in that slot, the general cancellation is omitted.
        """
        # Group records by (Class, Period)
        groups = {}
        for rec in records:
            key = (rec.get("Class", ""), rec.get("Period", ""))
            groups.setdefault(key, []).append(rec)

        final_list = []
        for key, recs in groups.items():
            # Identify a general cancellation record: Group == "" and Resolution == "odpadá"
            general_cancel = None
            # Build a list for records that have a non-empty Group OR are not cancellations
            subgroup_records = []  # records for a specific subgroup (Group not empty) OR a substitution for entire class
            for r in recs:
                group = r.get("Group", "").strip()
                resolution = r.get("Resolution", "").strip()
                if group == "":
                    if resolution == "odpadá":
                        general_cancel = r  # record for the whole class cancellation
                    else:
                        # a record for the entire class that is a substitution,
                        # so treat it like a subgroup record.
                        subgroup_records.append(r)
                else:
                    # record for a specific subgroup
                    subgroup_records.append(r)

            # Now, if we have any subgroup records that are substitutions, we want to update them:
            subs = [r for r in subgroup_records if r.get("Resolution", "").strip() != "odpadá"]
            if subs:
                # If there is a general cancellation, use its Subject as the note if needed.
                if general_cancel is not None:
                    cancellation_subject = general_cancel.get("Subject", "").strip()
                    for r in subs:
                        if not r.get("Note", "").strip() and cancellation_subject:
                            r["Note"] = f"za {cancellation_subject}"
                # Then add all substitution records.
                final_list.extend(subs)
            else:
                # No substitution records exist for this slot.
                # In that case, if a general cancellation exists, output it.
                if general_cancel is not None:
                    final_list.append(general_cancel)
                else:
                    # Otherwise, output whatever records exist (this is a fallback)
                    final_list.extend(recs)

        return final_list



    def generate(self, output_format):
        raw_substitutions = self.extract_substitutions()
        substitutions = self.extract_final_substitutions2(raw_substitutions)

        if output_format == "csv":
            pd.DataFrame(substitutions).to_csv(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.csv", index=False, sep=";")
            return "CSV file generated."

        elif output_format == "html":
            env = Environment(loader=FileSystemLoader(self.template_folder))
            template = env.get_template("students.html")

            day_of_week = self.date.isoweekday()
            if day_of_week == 1:
                headerColor = "#4f34ca"  # Monday
            elif day_of_week == 2:
                headerColor = "#c038cf"  # Tuesday
            elif day_of_week == 3:
                headerColor = "#FB536A"  # Wednesday
            elif day_of_week == 4:
                headerColor = "#e56e2e"  # Thursday
            elif day_of_week == 5:
                headerColor = "#eaa72f"  # Friday
            elif day_of_week == 6:
                headerColor = "#a0ea48"  # Saturday
            elif day_of_week == 7:
                headerColor = "#19cc59"  # Sunday
            else:
                headerColor = "#0984e3"  # Fallback color

            czech_day_names = {
                1: "Pondělí",
                2: "Úterý",
                3: "Středa",
                4: "Čtvrtek",
                5: "Pátek",
                6: "Sobota",
                7: "Neděle"
            }
            localizedDay = czech_day_names.get(day_of_week, "Neznámý den")
            html_content = template.render(date=self.date.strftime('%d.%m.%Y'), substitutions=substitutions, headerColor=headerColor, day=localizedDay)

            with open(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return "HTML file generated."

        elif output_format == "pdf":
            HTML(filename=f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.html").write_pdf(f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.pdf")
            return "PDF file generated."

        elif output_format == 'png':
            pdf = f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}.pdf"

            doc = pymupdf.open(pdf)
            desired_dpi = 600
            zoom = desired_dpi / 72  # 72 DPI is the default resolution
            mat = pymupdf.Matrix(zoom, zoom)  # Create a transformation matrix for scaling
            # Loop through each page and save as a PNG image
            for page_number in range(doc.page_count):
                page = doc[page_number]
                # Render the page to an image (pixmap)
                pix = page.get_pixmap(matrix=mat)
                # Define output filename
                output_filename = f"{self._path}/suplovani_students_{self.date.strftime('%Y_%m_%d')}__{page_number + 1}.png"
                # Save the image
                pix.save(output_filename)
                print(f"Saved {output_filename}")
            return "Png(s) generated."

        else:
            return "Unsupported format!"
