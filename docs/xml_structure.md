# ŠkolaOnline XML Structure (What We Use)

This document maps the ŠkolaOnline XML elements to the fields we consume for student and teacher substitution exports.

## High-Level
- Root contains calendar date, metadata, teachers, subjects, classes/groups, rooms, events, absences, and substitution listings.
- We process two payload types:
  - Students: `VypisSuplovaniZaka`
  - Teachers: `VypisSuplovani`

## Global Metadata
- `Kalendar/Datum`: ISO date of the schedule. Used for filenames and header day names.
- `SuplovaniDruhAbsence`: Maps `SUPL_DRUH_ABSENCE_ID` → human-readable absence reason.

## Teachers & Subjects
- `Ucitel` / `Ucitel2`
  - `OSOBA_ID`: Teacher ID (primary key).
  - `Jmeno`, `Prijmeni`: Full name parts.
  - `Zkratka`: Abbreviation used in outputs.
- `Predmet`
  - `REALIZACE_ID`: Subject ID.
  - `Zkratka`: Subject abbreviation (displayed in reports).

## Classes, Groups, Rooms, Periods
- `Trida`
  - `SKUPINA_ID`: Class ID.
  - `Nazev`: Class name (e.g., `3A`).
- `TridaSkupinaSeminar`
  - `SKUPINA_ID`: Group/track ID.
  - `SKUPINA_ID_PARENT`: Parent class ID.
  - `Nazev`: Group/track name (empty means full class).
- `Mistnost`
  - `MISTNOST_ID`: Room ID.
  - `Zkratka`: Room code.
- `VyucovaciHodinaOd`
  - `OBDOBI_DNE_ID`: Period ID.
  - `Nazev`: Period label.
  - `HodinaOd`, `HodinaDo`: Start/end hour (supports ranges, e.g., `3-4`).

## Event Associations (Students XML)
- `UdalostStudijniSkupina`: `UDALOST_ID` → `SKUPINA_ID` (which class/group an event belongs to).
- `UdalostMistnost`: `UDALOST_ID` → `MISTNOST_ID` (rooms; can be multiple per event).
- `UdalostOsoba`: `UDALOST_ID` → `OSOBA_ID` (teachers assigned to event; can be multiple).

## Event Associations (Teachers XML)
- `UdalostStudijniSkupiny`: `UDALOST_ID` → `SKUPINA_ID` (class/group for the event).
- `KalendarovaUdalostMistnost`: `UDALOST_ID` → `MISTNOST_ID` (rooms).

## Absences
- `AbsenceZdrojeVeDni`
  - Fields: `SUPL_DRUH_ABSENCE_ID`, `UDALOST_ID`, `Od`, `Do`.
  - Time window mapped to periods via `SchoolSchedule.from_iso`.
- `AbsenceUcitele`
  - `UDALOST_ID` → `OSOBA_ID` (who is absent for that event/time window).

## Substitution Records
- Students: `VypisSuplovaniZaka`
  - Keys: `UDALOST_ID`, `OBDOBI_DNE_ID`, `REALIZACE_ID`, `ZpusobReseni` (Resolution), `Poznamka` (Note), `CasOd`, `CasDo`.
  - Resolved to: Class/Group (via `UdalostStudijniSkupina`), Period (via `OBDOBI_DNE_ID` or `CasOd/CasDo`), Subject (`REALIZACE_ID`), Room(s) (`UdalostMistnost` → `Mistnost`), Teacher/Abbrev (via `UdalostOsoba` → `Ucitel`), Resolution text, Note text.
- Teachers: `VypisSuplovani`
  - Keys: `UDALOST_ID`, `OBDOBI_DNE_ID`, `REALIZACE_ID`, `OSOBA_ID`, `ZpusobReseni`, `Poznamka`.
  - Resolved to: Teacher/Abbrev (`OSOBA_ID` → `Ucitel`), Subject, Period, Class (`UDALOST_ID` → `SKUPINA_ID`), Room(s) (`KalendarovaUdalostMistnost`), Resolution, Note.

## Semantics & Business Logic Hooks
- `ZpusobReseni`:
  - `"odpadá"` means cancellation. For students, a general cancellation (Group empty) is currently suppressed if any non-cancellation exists for the same Class+Period.
  - Other values imply some form of substitution/merge/room change.
- Period resolution:
  - Prefer `OBDOBI_DNE_ID` mapping; if `CasOd/CasDo` yields a different range, override with the time-derived range.
  - Day-end filtering may drop or clamp periods beyond configured limit.
- Groups:
  - Empty group → whole class; non-empty → subgroup/track; affects whether cancellations should be hidden when substitutions exist.

## What Is Critical to Us
- IDs → Names/Labels:
  - Teacher: `OSOBA_ID` → `Zkratka`/full name.
  - Class/Group: `SKUPINA_ID` → class name/group name.
  - Subject: `REALIZACE_ID` → subject abbreviation.
  - Room: `MISTNOST_ID` → room code.
  - Period: `OBDOBI_DNE_ID` → label (possibly a range).
- Event Joins:
  - `UDALOST_ID` is the join key linking substitutions to class/group, room, and teachers.
- Cancellation vs Substitution:
  - Resolution text drives whether an entry is treated as cancellation; current merge logic hides certain cancellations.
- Time Windows:
  - `CasOd/CasDo` and absence `Od/Do` are translated to period ranges for display and filtering.
