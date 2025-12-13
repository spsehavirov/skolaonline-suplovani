"""
Module for processing teacher and student substitution schedules from SkolaOnline.cz.

This module provides a common base class (`SuplovaniBase`) for handling XML parsing,
data extraction, and report generation for both teacher (`SuplovaniUcitele`) and
student (`SuplovaniZaci`) substitutions.

Features:
- **Base class (`SuplovaniBase`)** for shared XML parsing and extraction logic.
  - Extracts absence reasons and teacher-specific class mappings.
- **Dictionary-based lookup optimizations** for efficient data extraction.

Classes:
- `SuplovaniBase`: Handles common XML parsing and data extraction methods.

Dependencies:
- `datetime`
- `xml.etree.ElementTree` (ET)
"""

# pylint: disable=R0902
# pylint: disable=R0914

import xml.etree.ElementTree as ET
from datetime import datetime
import re

from .settings import Settings


class SuplovaniBase:
    """
    Base class for processing substitution schedules from SkolaOnline.cz.

    This class provides common functionality for extracting teacher, subject,
    classroom, and event mappings, and generating output reports in multiple formats.

    Subclasses (`SuplovaniZaci` and `SuplovaniUcitele`) should implement their
    specific data extraction methods if necessary.
    """

    def __init__(self, xml_file, settings: Settings, template_folder="templates"):
        # pylint: disable=R0902
        self.xml_file = xml_file
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        self.date = self._extract_date()
        self.template_folder = template_folder
        self._path = "."
        self.settings = settings

        # Extract mappings
        self.subject_mapping = self._extract_subjects()
        self.room_mapping = self._extract_classrooms()
        self.period_mapping = self._extract_periods()

    @staticmethod
    def get(record, key, default=""):
        """
        Retrieves the text content of a given XML key from a record.
        If the key is missing, returns the default value.

        Args:
            record (ElementTree.Element): The XML record to search in.
            key (str): The XML tag name to find.
            default (str, optional): The value to return if key is missing. Defaults to "".

        Returns:
            str: The extracted text value or the default value.
        """
        element = record.find(key)
        return (
            element.text
            if element is not None and element.text is not None
            else default
        )

    def classes_to_exclude(self):
        """Classes to be excluded from generation (only for studens subs.)"""
        return set(self.settings.get("exclude", []))

    def classes_to_include(self):
        """Classes to be included from generation (only for studens subs.)"""
        return set(self.settings.get("include", []))

    def export_path(self, path):
        """Set the internal path prefix for the file exports."""
        self._path = path

    def _extract_date(self):
        """Extracts the date from the XML file."""
        date_element = self.root.find(".//Kalendar/Datum")
        return (
            datetime.fromisoformat(date_element.text)
            if date_element is not None
            else None
        )

    def _extract_subjects(self):
        """Extracts subjects mapping from XML."""
        return {
            subject.find("REALIZACE_ID").text: subject.find("Zkratka").text
            for subject in self.root.findall(".//Predmet")
            if subject.find("REALIZACE_ID") is not None
            and subject.find("Zkratka") is not None
        }

    def _extract_classrooms(self):
        """Extracts classroom mapping from XML."""
        return {
            room.find("MISTNOST_ID").text: room.find("Zkratka").text
            for room in self.root.findall(".//Mistnost")
            if room.find("MISTNOST_ID") is not None and room.find("Zkratka") is not None
        }

    def _extract_periods(self):
        """Extracts period mapping from XML, handling multi-hour spans."""
        periods = {}
        for period in self.root.findall(".//VyucovaciHodinaOd"):
            period_id = period.find("OBDOBI_DNE_ID")
            name = period.find("Nazev")
            hodina_od = period.find("HodinaOd")
            hodina_do = period.find("HodinaDo")

            if period_id is not None and name is not None:
                period_id_text = period_id.text
                period_name = name.text

                # EDITED: Handle multi-hour periods
                if (
                    hodina_od is not None
                    and hodina_do is not None
                    and hodina_od.text != hodina_do.text
                ):
                    period_name = f"{hodina_od.text}-{hodina_do.text}"  # Show as range

                periods[period_id_text] = period_name  # Store updated period name

        return periods

    def day_end_period(self):
        """
        Optional config for filtering records to the given last school period.

        Supported config keys (under `settings:` in config.yaml):
        - `day_end_period`
        - `day_end_hour` (alias)

        Returns:
            int | None: Last period to include, or None if not configured.
        """
        raw = self.settings.get("day_end_period", None)
        if raw is None:
            raw = self.settings.get("day_end_hour", None)

        if raw is None:
            return None

        if isinstance(raw, int):
            return raw if raw > 0 else None

        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return None
            if raw.isdigit():
                value = int(raw)
                return value if value > 0 else None

        return None

    @staticmethod
    def _parse_period_range(period_text: str):
        """
        Parse a period label into (start, end) numbers.
        Accepts values like "3", "3-4", "2nd", "1. hod", "celý den".
        """
        if not period_text:
            return None

        normalized = period_text.strip().lower()
        if not normalized:
            return None

        if "cel" in normalized and "den" in normalized:
            return (1, 99)

        nums = [int(n) for n in re.findall(r"\d+", normalized)]
        if not nums:
            return None

        if len(nums) == 1:
            return (nums[0], nums[0])

        start, end = nums[0], nums[1]
        return (min(start, end), max(start, end))

    def filter_records_by_end_period(self, records, period_key="Period"):
        """
        Filters records based on configured `day_end_period` / `day_end_hour`.

        Records with period ranges that extend past the end period are kept,
        but the `Period` label is clamped for display (e.g. "4-7" -> "4-5").
        """
        end_period = self.day_end_period()
        if not end_period:
            return records

        filtered = []
        for rec in records:
            period_text = rec.get(period_key, "")
            parsed = self._parse_period_range(period_text)
            if not parsed:
                filtered.append(rec)
                continue

            start, end = parsed
            if start > end_period:
                continue

            if end > end_period:
                rec = dict(rec)
                rec[period_key] = (
                    str(start) if start == end_period else f"{start}-{end_period}"
                )
            filtered.append(rec)

        return filtered

    def generate(self, output_format):
        """Generate the output in the specified format (CSV, HTML, PDF)."""
        raise NotImplementedError("This method should be implemented in subclasses.")
