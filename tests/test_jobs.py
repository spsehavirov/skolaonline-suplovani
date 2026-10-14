"""Exercise both CLI boundaries and the local downloader-to-monitor handoff."""

# Test names describe the cases; separate method docstrings would repeat them.
# pylint: disable=missing-function-docstring

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

import so_download
import so_soap
import suplovani
from supl import Settings
from supl.filters import FilterPolicy, parse_skip
from supl.jobs import archive_xml, prepare_download, publish_xml, settings_for_xml, sidecar_path
from tests.test_exports import XML


DAY = date(2026, 10, 14)


class JobTests(unittest.TestCase):
    """Check independent report jobs and failures without network requests."""

    def setUp(self):
        # enterContext registers cleanup for the entire test, beyond setUp's scope.
        # pylint: disable=consider-using-with
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.config_path = self.directory / "config.yaml"
        self.config = {
            "settings": {
                "watch_folder": str(self.directory / "watch"),
                "output_folder": str(self.directory / "outputs"),
                "output": ["csv", "html"],
                "include": [],
                "exclude": [],
            }
        }
        self.write_config()

    def write_config(self):
        self.config_path.write_text(yaml.safe_dump(self.config), encoding="utf-8")

    def publish(self, day=DAY, policy=FilterPolicy()):
        content = XML.replace(DAY.isoformat(), day.isoformat()).encode()
        return Path(publish_xml(content, day, self.config, policy))

    def process(self, xml):
        with (
            patch.object(suplovani, "config", Settings(self.config_path)),
            patch.object(
                suplovani, "PROCESSED_FOLDER", str(self.directory / "watch" / "processed")
            ),
        ):
            return suplovani.process_suplovani(xml)

    def test_cli_keeps_config_and_operational_settings(self):
        self.config["settings"].update(exclude=["3A"], day_end_hour=4)
        self.write_config()
        before = self.config_path.read_bytes()
        for script in (so_soap, so_download):
            args = script.build_parser().parse_args(["--no-config", "--hours=3-6", "--skip=4"])
            config, day, policy = prepare_download(self.config_path, "14.10.2026", args)
            self.assertEqual(day, DAY)
            self.assertEqual(
                config["settings"]["watch_folder"], self.config["settings"]["watch_folder"]
            )
            self.assertEqual(config["settings"]["output"], ["csv", "html"])
            self.assertEqual(policy.exclude, ())
            self.assertIsNone(policy.day_end_hour)
            self.assertEqual(policy.hours, (3, 6))
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_publication_order_and_complete_snapshot(self):
        real_link = os.link
        observed = []

        def observe(source, target):
            target = Path(target)
            if target.suffix == ".xml":
                self.assertFalse(target.exists())
                snapshot = json.loads(sidecar_path(target).read_text(encoding="utf-8"))
                self.assertEqual(snapshot["date"], DAY.isoformat())
                self.assertEqual(snapshot["filters"]["skip"], ["1-3:2-4"])
                observed.append("xml")
            else:
                observed.append("filters")
            return real_link(source, target)

        with patch("supl.jobs.os.link", side_effect=observe):
            xml = self.publish(policy=FilterPolicy(skip=parse_skip("1-3:2-4")))
        self.assertEqual(observed, ["filters", "xml"])
        self.assertEqual(xml.read_text(encoding="utf-8"), XML)

    def test_collision_preserves_pending_pair(self):
        xml = self.publish(policy=FilterPolicy(skip=parse_skip("1")))
        snapshot = sidecar_path(xml).read_bytes()
        with self.assertRaises(FileExistsError):
            self.publish(policy=FilterPolicy(skip=parse_skip("2")))
        self.assertEqual(xml.read_text(encoding="utf-8"), XML)
        self.assertEqual(sidecar_path(xml).read_bytes(), snapshot)

    def test_failed_publication_removes_its_sidecar(self):
        real_link = os.link

        def fail_xml(source, target):
            if Path(target).suffix == ".xml":
                raise OSError("publication failed")
            return real_link(source, target)

        with patch("supl.jobs.os.link", side_effect=fail_xml), self.assertRaises(OSError):
            self.publish()
        self.assertEqual(list((self.directory / "watch").iterdir()), [])

    def test_wrong_xml_date_rejected_before_publication(self):
        with self.assertRaisesRegex(ValueError, "does not match requested date"):
            publish_xml(XML.encode(), date(2026, 10, 15), self.config, FilterPolicy())
        self.assertFalse((self.directory / "watch").exists())

    def test_multiple_dates_and_changed_config_do_not_change_snapshots(self):
        first = self.publish(policy=FilterPolicy(skip=parse_skip("3A:1")))
        second = self.publish(date(2026, 10, 15), FilterPolicy(skip=parse_skip("3A:2")))
        self.config["settings"]["exclude"] = ["3A"]
        self.write_config()
        settings = Settings(self.config_path)
        a = settings_for_xml(first, settings).get("_filter_policy")
        b = settings_for_xml(second, settings).get("_filter_policy")
        self.assertTrue(a.allows_class("3A"))
        self.assertTrue(b.allows_class("3A"))
        self.assertEqual([r.to_text() for r in a.skip], ["3A:1"])
        self.assertEqual([r.to_text() for r in b.skip], ["3A:2"])

    def test_manual_xml_uses_fresh_date_specific_config(self):
        self.config["settings"]["student_filters_by_date"] = {DAY.isoformat(): {"skip": ["3A:1"]}}
        self.write_config()
        xml = self.directory / "manual.xml"
        xml.write_text(XML, encoding="utf-8")
        settings = Settings(self.config_path, cache_ttl=999)
        self.assertEqual(
            settings_for_xml(xml, settings).get("_filter_policy").skip, parse_skip("3A:1")
        )
        self.config["settings"]["student_filters_by_date"][DAY.isoformat()]["skip"] = ["3A:2"]
        self.write_config()
        self.assertEqual(
            settings_for_xml(xml, settings).get("_filter_policy").skip, parse_skip("3A:2")
        )

    def test_monitor_exports_and_archives_the_pair(self):
        xml = self.publish(policy=FilterPolicy(skip=parse_skip("1-3:1")))
        with redirect_stdout(io.StringIO()):
            self.assertTrue(self.process(xml))
        self.assertFalse(xml.exists())
        self.assertFalse(sidecar_path(xml).exists())
        archived = self.directory / "watch" / "processed" / xml.name
        self.assertTrue(archived.exists())
        self.assertTrue(sidecar_path(archived).exists())
        html = next((self.directory / "outputs").glob("*.html")).read_text(encoding="utf-8")
        self.assertNotIn("Test exportu", html)
        self.assertEqual(
            next((self.directory / "outputs").glob("*.csv")).read_text(encoding="utf-8").strip(), ""
        )
        self.assertEqual(
            settings_for_xml(archived, Settings(self.config_path)).get("_filter_policy").skip,
            parse_skip("1-3:1"),
        )

    def test_invalid_sidecar_leaves_inputs_and_outputs_untouched(self):
        mutations = [
            lambda data: data.update(date="2026-10-15"),
            lambda data: data.update(xml="other.xml"),
            lambda data: data.update(version=2),
            lambda data: data["filters"].update(hours=[True, 4]),
        ]
        xml = self.publish()
        original = sidecar_path(xml).read_text(encoding="utf-8")
        output = self.directory / "outputs" / "old.html"
        output.parent.mkdir()
        output.write_text("keep original output", encoding="utf-8")
        for change in mutations:
            data = json.loads(original)
            change(data)
            sidecar_path(xml).write_text(json.dumps(data), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertFalse(self.process(xml))
            self.assertTrue(xml.exists())
            self.assertTrue(sidecar_path(xml).exists())
            self.assertEqual(output.read_text(encoding="utf-8"), "keep original output")
            self.assertFalse((self.directory / "watch" / "processed").exists())
        sidecar_path(xml).write_text("not JSON", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertFalse(self.process(xml))
        self.assertEqual(output.read_text(encoding="utf-8"), "keep original output")

    def test_archive_collision_preserves_original_names_and_old_snapshots(self):
        first = self.publish(policy=FilterPolicy(skip=parse_skip("1")))
        processed = self.directory / "watch" / "processed"
        archived_a = archive_xml(first, processed)
        second = self.publish(policy=FilterPolicy(skip=parse_skip("2")))
        archived_b = archive_xml(second, processed)
        self.assertNotEqual(archived_a, archived_b)
        self.assertEqual(archived_a.name, archived_b.name)
        self.assertEqual(
            json.loads(sidecar_path(archived_a).read_text(encoding="utf-8"))["filters"]["skip"],
            ["1"],
        )
        self.assertEqual(
            json.loads(sidecar_path(archived_b).read_text(encoding="utf-8"))["filters"]["skip"],
            ["2"],
        )

    def test_archive_link_failure_keeps_both_inputs(self):
        xml = self.publish()
        real_link = os.link

        def fail_sidecar(source, target):
            if str(target).endswith(".filters.json"):
                raise OSError("archive failed")
            return real_link(source, target)

        with patch("supl.jobs.os.link", side_effect=fail_sidecar), self.assertRaises(OSError):
            archive_xml(xml, self.directory / "watch" / "processed")
        self.assertTrue(xml.exists())
        self.assertTrue(sidecar_path(xml).exists())
        self.assertFalse((self.directory / "watch" / "processed" / xml.name).exists())

    def test_monitor_retries_changed_jobs_without_spamming_unchanged_failures(self):
        xml = self.publish()
        ticks = 0

        def tick(_):
            nonlocal ticks
            ticks += 1
            if ticks == 3:
                sidecar_path(xml).write_text("changed and longer", encoding="utf-8")
            if ticks == 4:
                raise KeyboardInterrupt

        with (
            patch.object(suplovani, "WATCH_FOLDER", str(xml.parent)),
            patch.object(suplovani, "config", Settings(self.config_path)),
            patch.object(suplovani.time, "sleep", side_effect=tick),
            patch.object(suplovani, "process_suplovani", return_value=False) as process,
            redirect_stdout(io.StringIO()),
        ):
            with self.assertRaises(KeyboardInterrupt):
                suplovani.monitor_folder()
        self.assertEqual(process.call_count, 2)

    def test_soap_cli_download_handoff_without_network(self):
        before = self.config_path.read_bytes()
        with (
            patch.object(so_soap, "CONFIG", self.config_path),
            patch("sys.argv", ["so_soap.py", "--date=2026-10-14", "--no-config", "--skip=3A:1"]),
            patch.object(so_soap, "_ensure_credentials"),
            patch.object(so_soap, "_login"),
            patch.object(so_soap, "_download_xml", return_value=XML.encode()),
            patch.object(so_soap.requests, "Session"),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(so_soap.main(), 0)
        xml = next((self.directory / "watch").glob("*.xml"))
        self.assertEqual(
            json.loads(sidecar_path(xml).read_text(encoding="utf-8"))["filters"]["skip"], ["3A:1"]
        )
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_malformed_download_reports_failure_without_publishing(self):
        with (
            patch.object(so_soap, "CONFIG", self.config_path),
            patch("sys.argv", ["so_soap.py", "--date=2026-10-14"]),
            patch.object(so_soap, "_ensure_credentials"),
            patch.object(so_soap, "_login"),
            patch.object(so_soap, "_download_xml", return_value=b"<NewDataSet>broken"),
            patch.object(so_soap.requests, "Session"),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(so_soap.main(), 1)
        self.assertFalse((self.directory / "watch").exists())

    def test_invalid_cli_stops_before_download_or_launch(self):
        before = self.config_path.read_bytes()
        for script, boundary in ((so_soap, "_ensure_credentials"), (so_download, "runtime_job")):
            with (
                self.subTest(script=script.__name__),
                patch.object(script, "CONFIG", self.config_path),
                patch("sys.argv", [script.__name__, "--skip=1A:4-2"]),
                patch.object(script, boundary) as called,
                patch.object(so_download.subprocess, "call") as launch,
                redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as exc:
                    script.main()
                self.assertEqual(exc.exception.code, 2)
                called.assert_not_called()
                launch.assert_not_called()
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_selenium_subprocess_receives_snapshot_and_exit_code(self):
        before = self.config_path.read_bytes()

        def fake_launch(command):
            self.assertIn("--headless", command)
            self.assertFalse(any(arg.startswith("--skip") for arg in command))
            config, day, policy = so_download.runtime_job()
            self.assertEqual(day, DAY)
            self.assertEqual(
                config["settings"]["watch_folder"], self.config["settings"]["watch_folder"]
            )
            self.assertEqual(policy.skip, parse_skip("1-3:2-4"))
            return 7

        with (
            patch.object(so_download, "CONFIG", self.config_path),
            patch(
                "sys.argv", ["so_download.py", "--date=2026-10-14", "--skip=1-3:2-4", "--headless"]
            ),
            patch.dict(os.environ, {so_download.JOB_CONTEXT: "previous context"}),
            patch.object(so_download.subprocess, "call", side_effect=fake_launch),
        ):
            self.assertEqual(so_download.main(), 7)
            self.assertEqual(os.environ[so_download.JOB_CONTEXT], "previous context")
        self.assertEqual(self.config_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
