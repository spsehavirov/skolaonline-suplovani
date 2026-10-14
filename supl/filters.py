"""Shared, immutable filter policies for downloaded and manually supplied XML."""

import argparse
from dataclasses import dataclass
from datetime import date, datetime
import re
import warnings


NUMBER = r"[1-9][0-9]*"
RANGE = rf"{NUMBER}(?:-{NUMBER})?"
CLASS = rf"{NUMBER}[A-Z]+"
SELECTORS = rf"(?:{CLASS}(?:,{CLASS})*|{RANGE})"
SKIP = re.compile(rf"(?:(?P<classes>{SELECTORS}):)?(?P<periods>{RANGE})(?:,|$)")


def positive_period(value):
    if isinstance(value, bool) or not re.fullmatch(NUMBER, str(value).strip()):
        raise ValueError(f"Expected a positive school period, got {value!r}")
    return int(value)


def parse_range(value):
    if not isinstance(value, str):
        raise ValueError("A period range must be text, e.g. 3-6")
    value = re.sub(r"\s+", "", value)
    if not re.fullmatch(RANGE, value):
        raise ValueError(f"Invalid period range {value!r}; use 3 or 3-6")
    bounds = [int(part) for part in value.split("-")]
    start, end = bounds[0], bounds[-1]
    if start > end:
        raise ValueError(f"Reversed period range {value!r}")
    return start, end


def parse_date(value=None):
    if not value:
        return datetime.today().date()
    if not isinstance(value, str):
        raise ValueError("Date must be text, e.g. 2026-10-20")
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {value}")


@dataclass(frozen=True)
class SkipRule:
    selectors: tuple[str, ...]
    start: int
    end: int

    def matches(self, class_name):
        if not self.selectors:
            return True
        class_name = str(class_name).strip().upper()
        year = re.match(r"^([0-9]+)[A-Z]", class_name)
        for selector in self.selectors:
            if selector == class_name:
                return True
            if re.fullmatch(RANGE, selector) and year:
                first, last = parse_range(selector)
                if first <= int(year[1]) <= last:
                    return True
        return False

    def to_text(self):
        prefix = ",".join(self.selectors) + ":" if self.selectors else ""
        periods = str(self.start) if self.start == self.end else f"{self.start}-{self.end}"
        return prefix + periods


def parse_skip(value):
    if not isinstance(value, str):
        raise ValueError("A skip rule must be text, e.g. 1A:2-4")
    value = re.sub(r"\s+", "", value).upper()
    if not value or value.endswith(","):
        raise ValueError("Empty or incomplete --skip rule")
    rules, position = [], 0
    while position < len(value):
        match = SKIP.match(value, position)
        if not match:
            raise ValueError(f"Invalid --skip rule near {value[position:]!r}")
        selectors = tuple((match["classes"] or "").split(",")) if match["classes"] else ()
        for selector in selectors:
            if re.fullmatch(RANGE, selector):
                parse_range(selector)  # Reject reversed year ranges, too.
        start, end = parse_range(match["periods"])
        rules.append(SkipRule(selectors, start, end))
        position = match.end()
    return tuple(rules)


def _argument(parser):
    def convert(value):
        try:
            return parser(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc
    return convert


def add_filter_arguments(parser):
    parser.add_argument("--include", help="Comma-separated classes to include for this XML")
    parser.add_argument("--exclude", help="Comma-separated classes to exclude (always wins)")
    parser.add_argument("--clear", action="store_true", help="Ignore saved include/exclude for this XML")
    parser.add_argument("--day-end-hour", type=_argument(positive_period), help="Last period for student and teacher reports")
    parser.add_argument("--hours", type=_argument(parse_range), help="Student report window, e.g. 3-6")
    parser.add_argument("--skip", action="append", type=_argument(parse_skip), help="Student periods to omit, e.g. 2-4 or 1A,1B:2-4; repeatable")
    parser.add_argument("--no-config", action="store_true", help="Ignore saved filters; keep operational settings")


def _classes(values):
    if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Class filters must be lists of nonempty class names")
    return tuple(sorted({value.strip().upper() for value in values}))


@dataclass(frozen=True)
class FilterPolicy:
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    day_end_hour: int | None = None
    hours: tuple[int, int] | None = None
    skip: tuple[SkipRule, ...] = ()

    def allows_class(self, class_name):
        class_name = str(class_name).strip().upper()
        return class_name not in self.exclude and (not self.include or class_name in self.include)

    def to_dict(self):
        hours = None
        if self.hours is not None:
            hours = list(self.hours) if self.hours[0] <= self.hours[1] else []
        return {"include": list(self.include), "exclude": list(self.exclude),
                "day_end_hour": self.day_end_hour, "hours": hours,
                "skip": [rule.to_text() for rule in self.skip]}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"include", "exclude", "day_end_hour", "hours", "skip"}:
            raise ValueError("Invalid filter snapshot fields")
        end = data["day_end_hour"]
        if end is not None:
            if type(end) is not int:
                raise ValueError("Invalid end period in filter snapshot")
            end = positive_period(end)
        hours = data["hours"]
        if hours == []:
            hours = (1, 0)  # Empty intersection of otherwise valid windows.
        elif hours is not None:
            if not isinstance(hours, list) or len(hours) != 2 or any(type(n) is not int for n in hours):
                raise ValueError("Invalid hours in filter snapshot")
            hours = parse_range(f"{hours[0]}-{hours[1]}")
        skips = data["skip"]
        if not isinstance(skips, list):
            raise ValueError("Invalid skip list in filter snapshot")
        return cls(_classes(data["include"]), _classes(data["exclude"]), end,
                   hours, tuple(rule for item in skips for rule in parse_skip(item)))


def build_policy(settings, report_date: date, args=None):
    """Saved rules are the baseline; CLI adds constraints without changing them."""
    def option(name, default=None):
        return getattr(args, name, default)

    saved = {} if option("no_config", False) else settings
    include = [] if option("clear", False) else list(_classes(saved.get("include", [])))
    exclude = [] if option("clear", False) else list(_classes(saved.get("exclude", [])))
    for name, values in (("include", include), ("exclude", exclude)):
        if option(name) is not None:
            values.extend(option(name).split(","))
    end = saved.get("day_end_period")
    if end is None:
        end = saved.get("day_end_hour")
    end = positive_period(end) if end is not None else None
    if option("day_end_hour") is not None:
        cli_end = positive_period(option("day_end_hour"))
        end = min(end, cli_end) if end is not None else cli_end

    dated = saved.get("student_filters_by_date", {})
    if not isinstance(dated, dict):
        raise ValueError("student_filters_by_date must be a mapping keyed by ISO dates")
    # YAML also decodes unquoted ISO date keys as datetime.date objects.
    daily = dated.get(report_date.isoformat(), dated.get(report_date, {}))
    if not isinstance(daily, dict):
        raise ValueError("A dated student filter must be a mapping")
    hours = parse_range(daily["hours"]) if daily.get("hours") is not None else None
    if option("hours") is not None:
        cli_hours = option("hours")
        hours = (max(hours[0], cli_hours[0]), min(hours[1], cli_hours[1])) if hours else cli_hours
    skips = daily.get("skip", [])
    if not isinstance(skips, list):
        raise ValueError("Saved skip rules must be a list")
    rules = [rule for item in skips for rule in parse_skip(item)]
    for batch in option("skip", []) or []:
        rules.extend(batch)
    return FilterPolicy(_classes(include), _classes(exclude), end, hours,
                        tuple(dict.fromkeys(rules)))


def parse_period_label(value, all_day_end=99):
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().lower()
    if "cel" in normalized and "den" in normalized:
        return 1, all_day_end
    numbers = [int(n) for n in re.findall(r"\d+", normalized)]
    if not numbers or any(number < 1 for number in numbers[:2]):
        return None
    return min(numbers[:2]), max(numbers[:2])


def filter_records(records, policy, *, students, all_day_end=8, period_key="Period"):
    result, warned = [], set()
    for record in records:
        if students and not policy.allows_class(record.get("Class", "")):
            continue
        if students and policy.hours is not None and policy.hours[0] > policy.hours[1]:
            continue
        rules = tuple(rule for rule in policy.skip if rule.matches(record.get("Class", ""))) if students else ()
        window = policy.hours if students else None
        if policy.day_end_hour is None and window is None and not rules:
            result.append(record)
            continue
        label = record.get(period_key, "")
        bounds = parse_period_label(label, all_day_end)
        if bounds is None:
            if str(label) not in warned:
                warnings.warn(f"Cannot filter unrecognized period {label!r}; keeping the record", RuntimeWarning, stacklevel=2)
                warned.add(str(label))
            result.append(record)
            continue
        start, end = bounds
        if window is not None:
            start, end = max(start, window[0]), min(end, window[1])
        if policy.day_end_hour is not None:
            end = min(end, policy.day_end_hour)
        segments = [(start, end)] if start <= end else []
        for rule in rules:
            remaining = []
            for first, last in segments:
                if rule.end < first or rule.start > last:
                    remaining.append((first, last))
                else:
                    if first < rule.start:
                        remaining.append((first, rule.start - 1))
                    if last > rule.end:
                        remaining.append((rule.end + 1, last))
            segments = remaining
        if segments == [bounds]:
            result.append(record)
        else:
            for first, last in segments:
                result.append({**record, period_key: str(first) if first == last else f"{first}-{last}"})
    return result
