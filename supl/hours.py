"""
    Get info about the school hours and calculations on them
"""
from datetime import time, datetime

class SchoolSchedule:
    def __init__(self):
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

    def from_iso(self, from_iso_str, to_iso_str):
        from_dt = datetime.fromisoformat(from_iso_str)
        to_dt = datetime.fromisoformat(to_iso_str)
        return self._detect_periods(from_dt.time(), to_dt.time())

    def from_strings(self, from_str, to_str, time_format="%H:%M"):
        from_time = datetime.strptime(from_str, time_format).time()
        to_time = datetime.strptime(to_str, time_format).time()
        return self._detect_periods(from_time, to_time)

    def _detect_periods(self, from_time, to_time):
        detected_periods = []
        for period_name, (start_time, end_time) in self.periods.items():
            if from_time <= end_time and to_time >= start_time:
                detected_periods.append(period_name)

        if from_time == time(0, 0) and to_time == time(0, 0):
            return detected_periods, "celý den"

        if detected_periods:
            if detected_periods == list(self.periods.keys()) or len(detected_periods) >= 7:
                period_range = "celý den"
            elif detected_periods[0] == detected_periods[-1]:
                period_range = f"{detected_periods[0]}"  # Return single period instead of 5-5
            else:
                period_range = f"{detected_periods[0]}-{detected_periods[-1]}"
            return detected_periods, period_range
        else:
            return [], ""