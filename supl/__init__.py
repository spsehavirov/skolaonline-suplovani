"""
Module for importing teacher and student substitution processing classes.

This module provides access to the `SuplovaniUcitele` and `SuplovaniZaci`
classes, which handle XML parsing and report generation for teacher and
student substitutions.

Imports:
- `SuplovaniUcitele`: Handles teacher substitution processing.
- `SuplovaniZaci`: Handles student substitution processing.
- `Settings`: Settings helpers
- `SchoolSchedule`: Helpers to determine and manipulate school period times

Exports:
- `__all__`: Defines the public interface, limiting imports to the two classes.

Usage:
    from supl import SuplovaniUcitele, SuplovaniZaci, SchoolSchedule
"""
from .suplovani_teachers import SuplovaniUcitele
from .suplovani_students import SuplovaniZaci
from .settings import Settings
from .hours import SchoolSchedule

__all__ = ["SuplovaniUcitele", "SuplovaniZaci", "Settings", "SchoolSchedule"]
