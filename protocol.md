# Project summary

- Watches a configured folder for new ŠkolaOnline substitution XML files, detects teacher vs student exports, and generates CSV/HTML/PDF/PNG outputs, archiving processed XMLs.
- Student/teacher processors map subjects/teachers/rooms/periods, group events, apply include/exclude class filters from `config.yaml`, render HTML via Jinja, PDF via WeasyPrint, and per-page PNGs via PyMuPDF.
- `so_download.py` automates the browser with SeleniumBase to log in using `.env` creds, pick a date, update include/exclude filters, download the XML, and drop it into the watched folder.
- `so_soap.py` performs the same download via direct HTTP requests (no browser), producing the same filename pattern.
- `so_recorder.py` opens a logged-in Chrome session for manual interaction while capturing network traffic to JSON for later replay/reverse-engineering.
