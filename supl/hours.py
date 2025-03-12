"""
Module for handling school schedules
and calculating periods based on given time ranges.

Provides functionality to detect which school
periods a given time range overlaps with.
"""

from datetime import time, datetime

class SchoolSchedule:
    """
    Class to manage school periods and determine which periods are active
    within a given time range.
    """

    def __init__(self):
        """
        Initializes the schedule with predefined school periods.
        """
        self.periods = {
            "1": (time(7, 55), time(8, 40)),
            "2": (time(8, 45), time(9, 30)),
            "3": (time(9, 35), time(10, 20)),
            "4": (time(10, 30), time(11, 15)),
            "5": (time(11, 35), time(12, 20)),
            "6": (time(12, 25), time(13, 10)),
            "7": (time(13, 15), time(14, 00)),
            "8": (time(14, 5), time(14, 50)),
        }

    def from_iso(self, from_iso_str: str, to_iso_str: str):
        """
        Detects school periods based on ISO format timestamps.

        Args:
            from_iso_str (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
            to_iso_str (str): End time in ISO format (YYYY-MM-DDTHH:MM:SS).

        Returns:
            tuple: A list of detected periods and a string representation.
        """
        from_dt = datetime.fromisoformat(from_iso_str)
        to_dt = datetime.fromisoformat(to_iso_str)
        return self._detect_periods(from_dt.time(), to_dt.time())

    def from_strings(self, from_str: str, to_str: str, time_format: str = "%H:%M"):
        """
        Detects school periods based on time strings with a given format.

        Args:
            from_str (str): Start time as a string.
            to_str (str): End time as a string.
            time_format (str): Format of the input time strings (default: "%H:%M").

        Returns:
            tuple: A list of detected periods and a string representation.
        """
        from_time = datetime.strptime(from_str, time_format).time()
        to_time = datetime.strptime(to_str, time_format).time()
        return self._detect_periods(from_time, to_time)

    def _detect_periods(self, from_time: time, to_time: time):
        """
        Internal method to determine overlapping school periods.

        Args:
            from_time (time): Start time.
            to_time (time): End time.

        Returns:
            tuple: A list of detected periods and a string representation.
        """
        detected_periods = []

        # Check each period to see if it overlaps with the given time range
        for period_name, (start_time, end_time) in self.periods.items():
            if from_time <= end_time and to_time >= start_time:
                detected_periods.append(period_name)

        # If both times are midnight, assume full-day absence
        if from_time == time(0, 0) and to_time == time(0, 0):
            return detected_periods, "celý den"

        # Determine a textual representation of the period range
        if detected_periods:
            if detected_periods == list(self.periods.keys()) or len(detected_periods) >= 7:
                period_range = "celý den"
            elif detected_periods[0] == detected_periods[-1]:
                period_range = detected_periods[0]  # Single period case
            else:
                period_range = f"{detected_periods[0]}-{detected_periods[-1]}"
            return detected_periods, period_range

        return [], ""
