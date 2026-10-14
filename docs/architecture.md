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
1) `suplovani.py` loads `config.yaml` via `Settings` and resolves the watch directory and polling interval.
2) Watches `watch_folder`; on a new `*.xml`, detect type (`VypisSuplovaniZaka` → students, `VypisSuplovani` → teachers).
3) Read a fresh configuration snapshot and validate `<XML>.filters.json` if present. Otherwise build the policy from saved settings for the date inside the XML. Instantiate the matching processor with stable job settings, set export path, and call `generate` for each configured format.
4) Generated files go to `output_folder`; XML and filter metadata are archived together in `watch/processed`. Repeated archives retain the original pair's names in a unique subdirectory.

## Components
- Entry/watcher: `suplovani.py` orchestrates watch, detect, process, move.
- Config: `config.yaml` + `supl/settings.py` (`Settings`) read YAML, expose getters, include/exclude, `day_end_hour`/`day_end_period`.
- Filter policy: `supl/filters.py` parses the shared CLI and saved dated rules, combines constraints, and splits partially excluded period ranges. Policies and per-job settings remain stable across export formats.
- Job handoff: `supl/jobs.py` publishes complete metadata before complete XML using exclusive hard links within the watched filesystem; pending pairs cannot be overwritten. Metadata contains schema version 1, XML basename, ISO report date, and the resolved policy. Validation precedes export cleanup.
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
  - `so_download.py`: SeleniumBase browser automation; uses `.env` creds; passes the per-run date, watch directory and resolved policy into its pytest subprocess through a temporary process environment variable; publishes the downloaded XML and metadata.
  - `so_soap.py`: Direct HTTP form/post downloader (no browser) with the same filter flags, publication and filename pattern. Neither downloader writes filter arguments into config or `.env`.
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
3) Apply the dated student window, legacy day-end limit and matching global/class/year skips. Intersect windows, subtract skips, and emit remaining contiguous ranges before merging.
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
- Include/exclude: Student class names are compared case-insensitively. A nonempty include list restricts eligible classes; exclude always removes a class, even if included. Saved and CLI lists are combined by union.
- Day-end filter: `day_end_period`/`day_end_hour` drops records starting after the limit; clamps ranges that overrun the limit.
- Dated student filters: `student_filters_by_date["YYYY-MM-DD"]` contains optional `hours` and `skip` values. `--hours` intersects with the saved window; repeated `--skip` arguments add omissions. `--no-config` ignores saved filters but retains operational settings; `--clear` ignores only saved include/exclude. Arguments apply only to their XML. New student filters do not alter teacher reports or absence summaries.
- Full-day labels are bounded by the school schedule and numeric XML period mappings. Unknown period labels are retained with a warning when a matching hour filter is active.
- Cancellation merge (students): General cancellation (Group empty, Resolution == "odpadá") is dropped when any non-odpadá exists for the same class+period, regardless of group. This can hide valid “odpadá” entries if another record exists—known behaviour to revisit.
- Absence filtering: Skips certain staff abbreviations from absences list.

## Outputs
- Students filenames: `supl_<yy-mm-dd>_<day>.{csv|html|pdf|png...}`; Teachers: `suplovani_<yyyy_mm_dd>.{...}`.
- HTML rendered via Jinja2; PDF via WeasyPrint reading generated HTML; PNG pages via PyMuPDF.

## Dependencies (runtime)
- Core: Python 3.13 (current), pandas, jinja2, weasyprint, pymupdf, colorama.
- Downloaders: seleniumbase, requests-toolbelt (for SOAP variant), dotenv.

## Error Handling & Logging
- Prints to stdout with colorama accents. Invalid CLI rules stop before downloading; malformed/date-mismatched metadata stops before export. Failed inputs remain available, and the watcher continues with other jobs. It retries when XML, metadata or configuration changes, instead of repeatedly retrying an unchanged failed job.

## Known Gaps / Risks
- Layout: Non-packaged script layout; relative imports; no standardized entry points.
- Cancellation merge may suppress true cancellations when any other record exists for the class+period.
- Synthetic unittest coverage of filter parsing/precedence, split ranges, date isolation, both downloader boundaries, publication/archive failures, monitor handoff and real CSV/PDF/PNG exports. GitHub Actions runs Pylint and these checks independently on Python 3.12 and 3.13; live download tests and pre-commit hooks are not provided.
- Templates tightly coupled to Jinja2; logic lives in template (groupby, sorting) rather than code-side view models.

## Modernisation Hooks (pre-analysis)
- Clear separation points: watcher (I/O), processors (parsing/domain), template rendering, exporters (HTML/PDF/PNG), downloaders.
- Candidate refactors: move to domain models, service layer, typed config, packaged CLI, template engine swap, and quality gates.

## T-Strings vs Jinja2 (context)
- Potential benefits of T-strings (PEP 750): fewer deps, compile-time validation of placeholders, tighter typing of context, reduced injection surface.
- Trade-offs: Less built-in templating power (loops/filters) unless re-implemented; requires Python 3.14; migration needs regression tests and/or fallback to Jinja2 during transition.
