"""Exercise dependency upgrades using synthetic data and temporary exports."""

# Test names describe the cases; separate method docstrings would repeat them.
# pylint: disable=missing-function-docstring

import csv
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from copy import deepcopy

import pymupdf
import yaml

from supl import Settings, SuplovaniUcitele, SuplovaniZaci


XML = """<NewDataSet>
<Kalendar><Datum>2026-10-14T00:00:00</Datum></Kalendar>
<Ucitel><OSOBA_ID>t1</OSOBA_ID><Jmeno>Jan</Jmeno><Prijmeni>Novák</Prijmeni><Zkratka>JN</Zkratka></Ucitel>
<Predmet><REALIZACE_ID>s1</REALIZACE_ID><Zkratka>MAT</Zkratka></Predmet>
<Mistnost><MISTNOST_ID>r1</MISTNOST_ID><Zkratka>101</Zkratka></Mistnost>
<Trida><SKUPINA_ID>c1</SKUPINA_ID><Nazev>3A</Nazev></Trida>
<TridaSkupinaSeminar><SKUPINA_ID>g1</SKUPINA_ID><SKUPINA_ID_PARENT>c1</SKUPINA_ID_PARENT><Nazev>Skupina A</Nazev></TridaSkupinaSeminar>
<VyucovaciHodinaOd><OBDOBI_DNE_ID>p1</OBDOBI_DNE_ID><Nazev>1</Nazev><HodinaOd>1</HodinaOd><HodinaDo>1</HodinaDo></VyucovaciHodinaOd>
<UdalostStudijniSkupina><UDALOST_ID>e1</UDALOST_ID><SKUPINA_ID>g1</SKUPINA_ID></UdalostStudijniSkupina>
<UdalostStudijniSkupiny><UDALOST_ID>e1</UDALOST_ID><SKUPINA_ID>g1</SKUPINA_ID></UdalostStudijniSkupiny>
<UdalostMistnost><UDALOST_ID>e1</UDALOST_ID><MISTNOST_ID>r1</MISTNOST_ID></UdalostMistnost>
<KalendarovaUdalostMistnost><UDALOST_ID>e1</UDALOST_ID><MISTNOST_ID>r1</MISTNOST_ID></KalendarovaUdalostMistnost>
<UdalostOsoba><UDALOST_ID>e1</UDALOST_ID><OSOBA_ID>t1</OSOBA_ID></UdalostOsoba>
<VypisSuplovaniZaka><UDALOST_ID>e1</UDALOST_ID><OBDOBI_DNE_ID>p1</OBDOBI_DNE_ID><REALIZACE_ID>s1</REALIZACE_ID><CasOd>2026-10-14T07:55:00</CasOd><CasDo>2026-10-14T08:40:00</CasDo><ZpusobReseni>supluje</ZpusobReseni><Poznamka>Test exportu</Poznamka></VypisSuplovaniZaka>
<VypisSuplovani><UDALOST_ID>e1</UDALOST_ID><OBDOBI_DNE_ID>p1</OBDOBI_DNE_ID><REALIZACE_ID>s1</REALIZACE_ID><OSOBA_ID>t1</OSOBA_ID><ZpusobReseni>supluje</ZpusobReseni><Poznamka>Test exportu</Poznamka></VypisSuplovani>
</NewDataSet>"""


class ExportCompatibilityTests(unittest.TestCase):
    """Verify actual CSV/PDF/PNG output using synthetic school schedules."""

    def test_student_hour_filters_preserve_absence_summary(self):
        root = ET.fromstring(XML)
        for tag, fields in (
            ("SuplovaniDruhAbsence", {"SUPL_DRUH_ABSENCE_ID": "a1", "Nazev": "nemoc"}),
            (
                "AbsenceZdrojeVeDni",
                {
                    "SUPL_DRUH_ABSENCE_ID": "a1",
                    "UDALOST_ID": "absence1",
                    "Od": "2026-10-14T07:55:00",
                    "Do": "2026-10-14T08:40:00",
                },
            ),
            ("AbsenceUcitele", {"UDALOST_ID": "absence1", "OSOBA_ID": "t1"}),
        ):
            element = ET.SubElement(root, tag)
            for key, value in fields.items():
                ET.SubElement(element, key).text = value
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            xml = directory / "schedule.xml"
            ET.ElementTree(root).write(xml, encoding="utf-8")
            config = directory / "config.yaml"
            config.write_text(
                'settings:\n  student_filters_by_date:\n    "2026-10-14":\n'
                '      hours: "3-6"\n      skip: ["1"]\n',
                encoding="utf-8",
            )
            report = SuplovaniZaci(
                xml, Settings(config), str(Path(__file__).resolve().parents[1] / "templates")
            )
            report.export_path(str(directory))
            self.assertEqual(report.filter_student_records(report.extract_substitutions()), [])
            self.assertEqual(
                report.extract_absences(),
                [
                    {
                        "Teacher": "Jan Novák",
                        "Reason": "nemoc",
                        "From": "07:55",
                        "To": "08:40",
                        "Periods": "1",
                    }
                ],
            )
            report.generate("html")
            self.assertIn("Jan Novák", next(directory.glob("*.html")).read_text(encoding="utf-8"))

    def test_filtered_csv_pdf_png_and_unchanged_teacher_report(self):
        # Exercise the full export sequence and both report types in one fixture.
        # pylint: disable=too-many-locals,too-many-statements
        root = ET.fromstring(XML)
        root.find("Trida/Nazev").text = "1A"
        root.find("VyucovaciHodinaOd/HodinaDo").text = "6"
        root.find("VypisSuplovaniZaka/CasDo").text = "2026-10-14T13:10:00"
        root.find("VypisSuplovaniZaka/Poznamka").text = "VisibleMarker"
        root.find("VypisSuplovani/Poznamka").text = "TeacherMarker"
        for tag, fields in (
            ("Trida", {"SKUPINA_ID": "c2", "Nazev": "3A"}),
            (
                "TridaSkupinaSeminar",
                {"SKUPINA_ID": "g2", "SKUPINA_ID_PARENT": "c2", "Nazev": "Skupina B"},
            ),
            ("UdalostStudijniSkupina", {"UDALOST_ID": "e2", "SKUPINA_ID": "g2"}),
        ):
            element = ET.SubElement(root, tag)
            for key, value in fields.items():
                ET.SubElement(element, key).text = value
        excluded = deepcopy(root.find("VypisSuplovaniZaka"))
        excluded.find("UDALOST_ID").text = "e2"
        excluded.find("Poznamka").text = "ExcludedMarker"
        root.append(excluded)

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            xml = directory / "schedule.xml"
            ET.ElementTree(root).write(xml, encoding="utf-8")
            config = directory / "config.yaml"
            settings = {
                "settings": {
                    "include": ["1A", "3A"],
                    "exclude": ["3A"],
                    "student_filters_by_date": {"2026-10-14": {"skip": ["1-3:2-4"]}},
                }
            }
            config.write_text(yaml.safe_dump(settings), encoding="utf-8")
            templates = str(Path(__file__).resolve().parents[1] / "templates")
            students = SuplovaniZaci(xml, Settings(config), templates)
            students.export_path(str(directory))
            students.generate("csv")
            with next(directory.glob("*.csv")).open(newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            self.assertEqual([row["Period"] for row in rows], ["1", "5-6"])
            self.assertEqual([row["Note"] for row in rows], ["VisibleMarker", "VisibleMarker"])
            self.assertTrue(all(row["Class"] == "1A" for row in rows))

            # Editing config between formats must not change this job's snapshot.
            config.write_text("settings: {exclude: [1A, 3A]}\n", encoding="utf-8")
            students.generate("html")
            students.generate("pdf")
            with pymupdf.open(next(directory.glob("*.pdf"))) as document:
                text = "".join(page.get_text() for page in document)
                self.assertEqual(text.count("VisibleMarker"), 2)
                self.assertNotIn("ExcludedMarker", text)
                self.assertIn("5-6", text)
            students.generate("png")
            pngs = list(directory.glob("*.png"))
            self.assertTrue(pngs)
            self.assertTrue(all(png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for png in pngs))

            # The same saved hours/skip policy must leave teacher periods intact.
            config.write_text(yaml.safe_dump(settings), encoding="utf-8")
            teachers = SuplovaniUcitele(xml, Settings(config), templates)
            teachers.export_path(str(directory))
            teachers.generate("csv")
            with next(directory.glob("suplovani_*.csv")).open(newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            self.assertEqual([row["Period"] for row in rows], ["1-6"])
            teachers.generate("html")
            teachers.generate("pdf")
            with pymupdf.open(next(directory.glob("suplovani_*.pdf"))) as document:
                text = "".join(page.get_text() for page in document)
                self.assertIn("TeacherMarker", text)
                self.assertIn("1-6", text)

    def test_student_and_teacher_exports(self):
        for exporter in (SuplovaniZaci, SuplovaniUcitele):
            with self.subTest(exporter=exporter.__name__), tempfile.TemporaryDirectory() as folder:
                directory = Path(folder)
                xml = directory / "schedule.xml"
                xml.write_text(XML, encoding="utf-8")
                config = directory / "config.yaml"
                config.write_text("settings: {include: [], exclude: []}\n", encoding="utf-8")
                report = exporter(
                    xml, Settings(config), str(Path(__file__).resolve().parents[1] / "templates")
                )
                report.export_path(str(directory))

                report.generate("csv")
                rows = []
                for output in directory.glob("*.csv"):
                    with output.open(encoding="utf-8", newline="") as stream:
                        rows.extend(csv.DictReader(stream, delimiter=";"))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Subject"], "MAT")
                self.assertEqual(rows[0]["Room"], "101")
                self.assertEqual(rows[0]["Note"], "Test exportu")

                report.generate("html")
                report.generate("pdf")
                pdfs = list(directory.glob("*.pdf"))
                self.assertEqual(len(pdfs), 1)
                with pymupdf.open(pdfs[0]) as document:
                    self.assertGreater(document.page_count, 0)
                    text = "".join(page.get_text() for page in document)
                    self.assertIn("MAT", text)
                    self.assertIn("Test exportu", text)

                if exporter is SuplovaniZaci:
                    report.generate("png")
                    pngs = list(directory.glob("*.png"))
                    self.assertTrue(pngs)
                    for png in pngs:
                        self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
