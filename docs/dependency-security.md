# Dependency security update — 2026-10-14

Updated the existing pins to the latest stable releases available from PyPI.
Python 3.13 remains the supported installer target. No application APIs changed.

The installed dependency tree initially contained 23 distinct advisory IDs
across nine packages. The audit returned 40 entries because some advisories
appeared more than once. After the update, `pip-audit` reported no known
vulnerabilities, with no ignored advisories.

## Affected packages

| Package | Before | Verified after |
| --- | --- | --- |
| h11 | 0.14.0 | 0.16.0 |
| idna | 3.10 | 3.20 |
| lxml | 5.3.1 | 6.1.3 |
| pytest | 8.3.4 | 9.1.1 |
| python-dotenv | 1.0.1 | 1.2.4 |
| requests | 2.32.3 | 2.34.2 |
| soupsieve | 2.6 | 3.0.3 |
| urllib3 | 2.3.0 | 2.8.0 |
| WeasyPrint | 64.0 | 70.0 |

SeleniumBase 4.56.1 replaces 4.34.15 and requires the updated HTTP, HTML-parser,
and test dependencies above. Its old version constrained several dependencies
to vulnerable releases. Direct pins also update pandas to 3.0.6 and PyMuPDF to
1.28.2; export compatibility is checked by `tests/test_exports.py`.

WeasyPrint 70.0 fixes unsafe EPS image handling and URL-fetcher issues:
[upstream release notes](https://github.com/Kozea/WeasyPrint/blob/main/docs/changelog.rst).
Package release versions were checked using the [PyPI JSON API](https://docs.pypi.org/api/json/).
The audit uses [pip-audit](https://github.com/pypa/pip-audit) and its default PyPI
vulnerability service. Results describe known advisories at the time of the scan.

## Repeat verification

From the repository root:

```bash
./install
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v

# Keep audit tooling separate from the application environment.
python3.13 -m venv /tmp/so-supl-audit-tools
/tmp/so-supl-audit-tools/bin/python -m pip install pip-audit
/tmp/so-supl-audit-tools/bin/pip-audit \
  --cache-dir /tmp/so-supl-audit-cache \
  --path .venv/lib/python3.13/site-packages
```

Verified a clean installation and the upgraded project environment on macOS
arm64 with Python 3.13.15. The export check uses synthetic XML, checks CSV field
values, renders both student and teacher templates to PDF, checks the extracted
PDF text, and exercises student PNG generation. All output goes to temporary
directories; school data and configuration are not modified.

Live ŠkolaOnline login/download and browser automation were not exercised.
Fontconfig emitted cache-permission warnings in the restricted environment;
PDF and PNG generation still passed.
