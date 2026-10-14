"""Rules, precedence, dates and partial period ranges."""

# Test names describe the cases; separate method docstrings would repeat them.
# pylint: disable=missing-function-docstring

import argparse
from datetime import date
import io
from contextlib import redirect_stderr
import unittest

from supl.filters import (
    FilterPolicy,
    add_filter_arguments,
    build_policy,
    filter_records,
    parse_range,
    parse_skip,
)


DAY = date(2026, 10, 14)


def arguments(*values):
    parser = argparse.ArgumentParser()
    add_filter_arguments(parser)
    return parser.parse_args(values)


def record(period="1-6", class_name="1A", **other):
    return {
        "Class": class_name,
        "Period": period,
        "Subject": "MAT",
        "Group": ["A"],
        "Resolution": "supluje",
        "Note": "keep",
        **other,
    }


class FilterTests(unittest.TestCase):
    """Check filter behavior independently of downloading and rendering."""

    def test_requested_syntax(self):
        examples = {
            "2-4": [((), 2, 4)],
            "1A:2-4": [(("1A",), 2, 4)],
            "1A,1B,1C:2-4": [(("1A", "1B", "1C"), 2, 4)],
            "1-3:2-4": [(("1-3",), 2, 4)],
            "1A:2-4,1B:1-2,1C:4": [(("1A",), 2, 4), (("1B",), 1, 2), (("1C",), 4, 4)],
            " 1a, 1b : 2 - 4 ": [(("1A", "1B"), 2, 4)],
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(
                    [(r.selectors, r.start, r.end) for r in parse_skip(text)], expected
                )
        policy = build_policy({}, DAY, arguments("--skip=1A:2-4", "--skip=1B:1-2", "--skip=1C:4"))
        self.assertEqual(len(policy.skip), 3)

    def test_invalid_rules_rejected(self):
        for text in (
            "",
            "0",
            "-1",
            "4-2",
            "1A:",
            ":2",
            "1A:2-0",
            "3-1:2",
            "1A:2,",
            "1A:2,1B",
            "1A:2;1B:3",
            "2--4",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_skip(text)
        for text in ("0-3", "6-3", "abc", "2-3-4"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_range(text)
        for args in (("--hours=6-3",), ("--skip=1A:0",), ("--day-end-hour=0",)):
            with (
                self.subTest(args=args),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as exc,
            ):
                arguments(*args)
            self.assertEqual(exc.exception.code, 2)

    def test_years_match_all_divisions_and_not_prefixes(self):
        rule = parse_skip("1-3:2-4")[0]
        for name in ("1A", "1B", "1C", "2D", "3IT", " 3c "):
            self.assertTrue(rule.matches(name), name)
        for name in ("4A", "10A", "13C", "", "unknown"):
            self.assertFalse(rule.matches(name), name)
        self.assertTrue(parse_skip("2:1")[0].matches("2B"))
        self.assertFalse(parse_skip("1A:2")[0].matches("1B"))

    def test_saved_rules_and_cli_compose(self):
        settings = {
            "include": ["1A"],
            "exclude": ["1B"],
            "day_end_period": 5,
            "day_end_hour": 7,
            "student_filters_by_date": {DAY.isoformat(): {"hours": "2-7", "skip": ["1A:2"]}},
        }
        policy = build_policy(
            settings,
            DAY,
            arguments(
                "--include=1B", "--exclude=1C", "--hours=3-6", "--day-end-hour=8", "--skip=1A:4"
            ),
        )
        self.assertEqual(policy.include, ("1A", "1B"))
        self.assertEqual(policy.exclude, ("1B", "1C"))
        self.assertEqual(policy.day_end_hour, 5)
        self.assertEqual(policy.hours, (3, 6))
        self.assertFalse(policy.allows_class("1B"))
        rows = filter_records([record("1-8")], policy, students=True)
        self.assertEqual([row["Period"] for row in rows], ["3", "5"])
        self.assertEqual(settings["exclude"], ["1B"])

    def test_date_isolation(self):
        settings = {
            "student_filters_by_date": {DAY.isoformat(): {"hours": "3-6", "skip": ["1-3:4"]}}
        }
        today = build_policy(settings, DAY)
        other = build_policy(settings, date(2026, 10, 15))
        self.assertEqual(today.hours, (3, 6))
        self.assertEqual(other, FilterPolicy())

    def test_yaml_date_keys_are_supported(self):
        policy = build_policy({"student_filters_by_date": {DAY: {"skip": ["2-4"]}}}, DAY)
        self.assertEqual(policy.skip, parse_skip("2-4"))

    def test_clear_and_no_config_are_distinct(self):
        settings = {
            "include": ["3A"],
            "exclude": ["1A"],
            "day_end_hour": 5,
            "student_filters_by_date": {DAY.isoformat(): {"skip": ["2"]}},
        }
        clear = build_policy(settings, DAY, arguments("--clear", "--include=1A"))
        self.assertTrue(clear.allows_class("1A"))
        self.assertEqual(clear.day_end_hour, 5)
        self.assertEqual(len(clear.skip), 1)
        clean = build_policy(settings, DAY, arguments("--no-config", "--hours=3-6", "--skip=4"))
        self.assertEqual(clean.include, ())
        self.assertEqual(clean.exclude, ())
        self.assertIsNone(clean.day_end_hour)
        self.assertEqual([rule.to_text() for rule in clean.skip], ["4"])

    def test_exclude_always_wins_and_names_are_case_insensitive(self):
        policy = build_policy({"include": ["1a", "3a"], "exclude": ["3A"]}, DAY)
        rows = filter_records(
            [record(class_name="1A"), record(class_name="3a"), record(class_name="2A")],
            policy,
            students=True,
        )
        self.assertEqual([row["Class"] for row in rows], ["1A"])

    def test_partial_range_splits_without_modifying_inputs(self):
        source = record()
        rows = filter_records([source], FilterPolicy(skip=parse_skip("1A:2-4")), students=True)
        self.assertEqual([row["Period"] for row in rows], ["1", "5-6"])
        self.assertEqual(source["Period"], "1-6")
        for row in rows:
            self.assertEqual(row["Note"], "keep")
            self.assertEqual(row["Group"], ["A"])

    def test_complete_removal_and_overlapping_skips(self):
        policy = FilterPolicy(skip=parse_skip("2-4,1A:3-5"))
        rows = filter_records(
            [record("1-6"), record("2-4"), record("6", "2B")], policy, students=True
        )
        self.assertEqual(
            [(row["Class"], row["Period"]) for row in rows], [("1A", "1"), ("1A", "6"), ("2B", "6")]
        )

    def test_empty_intersection_and_snapshot_round_trip(self):
        settings = {"student_filters_by_date": {DAY.isoformat(): {"hours": "1-2"}}}
        policy = build_policy(settings, DAY, arguments("--hours=3-6"))
        restored = FilterPolicy.from_dict(policy.to_dict())
        self.assertEqual(filter_records([record(), record("unknown")], restored, students=True), [])
        populated = build_policy(
            {},
            DAY,
            arguments(
                "--include=1A", "--exclude=3A", "--hours=3-6", "--skip=1A,1B:4", "--day-end-hour=5"
            ),
        )
        self.assertEqual(FilterPolicy.from_dict(populated.to_dict()), populated)

    def test_all_day_and_unrecognized_periods(self):
        policy = FilterPolicy(skip=parse_skip("2-4"))
        rows = filter_records([record("celý den")], policy, students=True, all_day_end=10)
        self.assertEqual([row["Period"] for row in rows], ["1", "5-10"])
        unknown = record("unknown")
        with self.assertWarnsRegex(RuntimeWarning, "keeping the record"):
            self.assertEqual(filter_records([unknown], policy, students=True), [unknown])

    def test_teacher_report_ignores_new_student_filters(self):
        policy = FilterPolicy(
            include=("2A",), exclude=("1A",), hours=(3, 5), skip=parse_skip("2-4")
        )
        self.assertEqual(filter_records([record()], policy, students=False), [record()])
        policy = FilterPolicy(day_end_hour=5, hours=(3, 5), skip=parse_skip("2-4"))
        rows = filter_records([record()], policy, students=False)
        self.assertEqual([row["Period"] for row in rows], ["1-5"])


if __name__ == "__main__":
    unittest.main()
