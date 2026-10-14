# Project summary

[User documentation](README.md) · [Architecture](docs/architecture.md)

- `suplovani.py` watches the configured folder, processes existing and changed XML,
  detects student vs teacher exports, and archives each XML/metadata pair.
- Student reports support CSV, HTML, PDF and per-page PNG; teacher reports support
  CSV, HTML and PDF. Templates use Jinja2, PDF uses WeasyPrint, and PNG uses PyMuPDF.
- `so_soap.py` downloads student substitution XML through the web application's HTTP
  form without Selenium or a browser. `so_download.py` provides the SeleniumBase variant.
- Both downloaders resolve saved and CLI filters into an immutable per-XML snapshot.
  CLI filters do not modify `config.yaml` or `.env`; class exclusions take precedence.
- Dated student filters provide hour windows and global/class/year skip rules.
  Teacher reports retain the shared day-end limit and ignore the new student-only rules.
- `so_recorder.py` records network requests during manual work in logged-in Chrome.
- The local installer targets Python 3.13. CI checks Pylint and synthetic regression
  tests on Python 3.12 and 3.13; live downloads are outside the automated test suite.
