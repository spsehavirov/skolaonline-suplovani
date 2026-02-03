# Architecture Overview

## Purpose
- Automate ingestion of ŠkolaOnline XML exports (students/teachers), transform them into CSV/HTML/PDF/PNG, and archive processed XMLs.
- Drive hallway/TV display content from the generated HTML/PDF/PNG outputs.

## Input Data (XML) — Key Elements and Mappings
- Common header:
  - `Kalendar/Datum`: ISO date of the schedule; used for filenames and display day name.
  - `SuplovaniDruhAbsence`: List of absence reason IDs → names.
- Teacher & subject metadata:
  - `Ucitel` / `Ucitel2`: `OSOBA_ID`, `Jmeno`, `Prijmeni`, `Zkratka` (short code).
  - `Predmet`: `REALIZACE_ID`, `Zkratka` (subject abbreviation).
- Classes and groups:
  - `Trida`: `SKUPINA_ID`, `Nazev` (class name).
  - `TridaSkupinaSeminar`: `SKUPINA_ID`, `SKUPINA_ID_PARENT` (class), `Nazev` (group/track name).
- Rooms & periods:
  - `Mistnost`: `MISTNOST_ID`, `Zkratka`.
  - `VyucovaciHodinaOd`: `OBDOBI_DNE_ID`, `Nazev`, `HodinaOd`, `HodinaDo` (supports multi-hour ranges).
- Event associations (students XML):
  - `UdalostStudijniSkupina`: `UDALOST_ID` → `SKUPINA_ID` (group assignment for an event).
  - `UdalostMistnost`: `UDALOST_ID` → `MISTNOST_ID` (rooms, can be multiple).
  - `UdalostOsoba`: `UDALOST_ID` → `OSOBA_ID` (teachers assigned to event).
- Event associations (teachers XML):
  - `UdalostStudijniSkupiny`: `UDALOST_ID` → `SKUPINA_ID`.
  - `KalendarovaUdalostMistnost`: `UDALOST_ID` → `MISTNOST_ID`.
- Absences:
  - `AbsenceZdrojeVeDni`: carries `SUPL_DRUH_ABSENCE_ID`, `UDALOST_ID`, `Od`, `Do`.
  - `AbsenceUcitele`: `UDALOST_ID` → `OSOBA_ID`.
- Substitution payloads:
  - Students: `VypisSuplovaniZaka` records with `UDALOST_ID`, `OBDOBI_DNE_ID`, `ZpusobReseni` (Resolution), `Poznamka`, `REALIZACE_ID`, `CasOd`/`CasDo`.
  - Teachers: `VypisSuplovani` records with analogous fields plus `OSOBA_ID`.

### Semantics
- `ZpusobReseni`: free text like “odpadá”, “supluje”, “spojeno”, etc.; drives cancellation/substitution logic.
- Period derivation: either from `OBDOBI_DNE_ID` mapping or from `CasOd/CasDo` → period range via `SchoolSchedule.from_iso`.
- Group handling: empty `Group` denotes full class; non-empty means subgroup/track; impacts cancellation suppression logic.

## Runtime Flow (current)
1) `suplovani.py` loads `config.yaml` via `Settings` and resolves `watch_folder`, `output_folder`, formats, include/exclude rules, and optional day-end limit.
2) Watches `watch_folder`; on a new `*.xml`, detect type (`VypisSuplovaniZaka` → students, `VypisSuplovani` → teachers).
3) Instantiate the matching processor (`SuplovaniZaci` or `SuplovaniUcitele`), set export path, and call `generate` for each configured format.
4) Generated files go to `output_folder`; the XML is moved to `watch/processed`.

## Components
- Entry/watcher: `suplovani.py` orchestrates watch, detect, process, move.
- Config: `config.yaml` + `supl/settings.py` (`Settings`) read YAML, expose getters, include/exclude, `day_end_hour`/`day_end_period`.
- Base processor: `supl/suplovani_base.py` parses XML, extracts mappings (subjects, rooms, periods), date, includes/excludes, clamps periods beyond end-of-day, and provides helpers.
- Student processor: `supl/suplovani_students.py`
  - Extracts teacher/class/group/event-room/event-teacher mappings.
  - Builds substitution dicts (Class, Period, Subject, Group, Room, Teacher/Abbrev, Resolution, Note).
  - Merges cancellations vs substitutions in `extract_final_substitutions2` (drops general “odpadá” if any non-cancellation exists for same class+period; fills missing notes with “za <Subject>”).
  - Renders `templates/students.html` via Jinja2; exports HTML → PDF (WeasyPrint) → PNG (PyMuPDF).
  - Absences extraction skips select staff abbreviations (KOP/HRN/HEI).
- Teacher processor: `supl/suplovani_teachers.py`
  - Extracts teacher absences and substitutions; simpler flow, no cancel/sub merge; renders `templates/teachers.html`.
- Hours helper: `supl/hours.py` maps ISO timestamps to period ranges for absence/substitution time windows.
- Downloaders:
  - `so_download.py`: SeleniumBase browser automation; uses `.env` creds; optional date/include/exclude/day-end flags; drops XML into watch folder.
  - `so_soap.py`: Direct HTTP form/post downloader (no browser) with the same flags and filename pattern.
  - `so_recorder.py`: Opens logged-in browser and records network traffic to JSON for reverse-engineering.
- Templates: `templates/students.html` and `templates/teachers.html`; inline CSS, Jinja2 templating.

## Data Transformation Steps (students)
1) Load XML and extract mappings (teachers, classes/groups, rooms, periods, event→group/room/teacher).
2) For each `VypisSuplovaniZaka` record:
   - Resolve `Class`/`Group` from `UDALOST_ID` → `SKUPINA_ID` mapping.
   - Resolve `Period` from `OBDOBI_DNE_ID`, fallback/override with `CasOd/CasDo` → range.
   - Resolve `Subject` from `REALIZACE_ID`.
   - Resolve `Room` (may be multiple, joined with comma) from `UdalostMistnost`.
   - Resolve `Teacher/Abbrev` list from `UdalostOsoba` → `OSOBA_ID` → teacher map.
   - Capture `Resolution`, `Note`.
   - Apply include/exclude on `Class`; drop if not allowed.
3) Apply day-end filter: drop records starting after configured end; clamp ranges crossing the limit.
4) Cancellation/substitution merge (`extract_final_substitutions2`):
   - Group by `(Class, Period)`.
   - Identify general cancellation (`Group == ""` and `Resolution == "odpadá"`).
   - If any non-cancellation exists, keep substitutions only; propagate “za <Subject>” into empty notes.
   - If no substitutions, keep the cancellation; else keep all records (fallback).
5) Export:
   - CSV: raw substitutions pre-merge (note: cancellations visible here even if hidden later).
   - HTML: render merged list; PDF via WeasyPrint from HTML; PNG snapshots via PyMuPDF.
6) Absences: collect `AbsenceZdrojeVeDni` + `AbsenceUcitele`, map times to periods, skip selected staff abbreviations.

## Data Transformation Steps (teachers)
1) Load XML and mappings (teachers, classes/groups, rooms, periods, event→group, event→room).
2) For each `VypisSuplovani` record:
   - Resolve Teacher/Abbrev from `OSOBA_ID`; Subject from `REALIZACE_ID`; Period from `OBDOBI_DNE_ID`; Class from `UDALOST_ID` → `SKUPINA_ID`; Room from `KalendarovaUdalostMistnost`.
   - Capture `Resolution`, `Note`.
3) Apply day-end filter (same helper).
4) Export CSV/HTML/PDF (no PNG path here).
5) Absences: map reasons and teacher IDs; no filtering by abbreviation.

## Data & Business Rules
- Data model (current): plain dicts for records; mappings keyed by IDs from XML.
- Include/exclude: For students, include list wins if present; otherwise exclude list filters by class name.
- Day-end filter: `day_end_period`/`day_end_hour` drops records starting after the limit; clamps ranges that overrun the limit.
- Cancellation merge (students): General cancellation (Group empty, Resolution == "odpadá") is dropped when any non-odpadá exists for the same class+period, regardless of group. This can hide valid “odpadá” entries if another record exists—known behaviour to revisit.
- Absence filtering: Skips certain staff abbreviations from absences list.

## Outputs
- Students filenames: `supl_<yy-mm-dd>_<day>.{csv|html|pdf|png...}`; Teachers: `suplovani_<yyyy_mm_dd>.{...}`.
- HTML rendered via Jinja2; PDF via WeasyPrint reading generated HTML; PNG pages via PyMuPDF.

## Dependencies (runtime)
- Core: Python 3.13 (current), pandas, jinja2, weasyprint, pymupdf, colorama.
- Downloaders: seleniumbase, requests-toolbelt (for SOAP variant), dotenv.

## Error Handling & Logging
- Minimal: prints to stdout with colorama accents; limited structured errors; watcher continues on unknown XML type.

## Known Gaps / Risks
- Layout: Non-packaged script layout; relative imports; no standardized entry points.
- Cancellation merge may suppress true cancellations when any other record exists for the class+period.
- Limited testing and no CI/pre-commit in repo.
- Templates tightly coupled to Jinja2; logic lives in template (groupby, sorting) rather than code-side view models.

## Modernisation Hooks (pre-analysis)
- Clear separation points: watcher (I/O), processors (parsing/domain), template rendering, exporters (HTML/PDF/PNG), downloaders.
- Candidate refactors: move to domain models, service layer, typed config, packaged CLI, template engine swap, and quality gates.

## T-Strings vs Jinja2 (context)
- Potential benefits of T-strings (PEP 750): fewer deps, compile-time validation of placeholders, tighter typing of context, reduced injection surface.
- Trade-offs: Less built-in templating power (loops/filters) unless re-implemented; requires Python 3.14; migration needs regression tests and/or fallback to Jinja2 during transition.
