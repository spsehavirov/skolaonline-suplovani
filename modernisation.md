# OpenSpec Features - SkolaOnline Suplování Modernisation

**Project:** SkolaOnline Suplování
**Version:** 2.0.0
**Date:** January 2026
**Status:** Planning Phase

---

## Feature: Python 3.14 Migration

**Priority:** Critical
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Upgrade codebase from Python 3.13 to Python 3.14 (released October 2025) to leverage latest language features including template strings, deferred annotation evaluation, type parameter defaults, and performance improvements.

### User Stories
- As a developer, I want to use Python 3.14 features so I can write cleaner, more efficient code
- As a user, I want the application to run on Python 3.14 so I benefit from performance improvements

### Acceptance Criteria
- [ ] All Python files specify `requires-python = ">=3.14"` in pyproject.toml
- [ ] GitHub Actions CI matrix includes Python 3.14
- [ ] All `from __future__ import annotations` statements removed
- [ ] Type syntax modernized (Union[X,Y] → X|Y, List[X] → list[X], etc.)
- [ ] Bracketless except syntax used (PEP 758)
- [ ] Codebase runs successfully on Python 3.14
- [ ] All tests pass on Python 3.14

### Technical Requirements
- Update `.pylintrc` to `py-version=3.14`
- Update `README.md` to specify Python 3.14 requirement
- Update `install` script to validate Python version >= 3.14
- Update CI configuration to test on Python 3.14

### Dependencies
- None (depends on Phase 0 completion)

### Notes
Free-threaded Python 3.14 available optionally for performance testing.

---

## Feature: Package Structure Restructure

**Priority:** Critical
**Complexity:** High
**Effort:** 3-4 hours

### Description
Restructure codebase to follow proper Python package layout with `src/skolaonline/` directory structure, implementing clean separation of concerns across domain, service, and infrastructure layers.

### User Stories
- As a developer, I want clear package structure so I can easily locate code
- As a maintainer, I want organized layers so I can test and modify components independently
- As a new contributor, I want standard Python project layout so I can understand codebase quickly

### Acceptance Criteria
- [ ] Create `src/skolaonline/` package directory
- [ ] Move `supl/` → `src/skolaonline/processors/`
- [ ] Move `templates/` → `src/skolaonline/templates/`
- [ ] Create subdirectories: `config/`, `core/`, `domain/`, `services/`, `downloaders/`, `utils/`
- [ ] Update all imports to use absolute paths from `skolaonline`
- [ ] Create proper `__init__.py` files with `__all__` exports
- [ ] Delete or archive old root-level scripts after migration

### Technical Requirements
- Directory structure:
  ```
  src/skolaonline/
  ├── __init__.py
  ├── cli.py
  ├── config/
  ├── core/
  ├── domain/
  ├── services/
  ├── downloaders/
  ├── processors/
  └── utils/
  ```
- Update all relative imports
- Ensure package is importable after installation

### Dependencies
- Python 3.14 Migration (Feature 1)

### Notes
This is breaking change - requires updating documentation and scripts.

---

## Feature: Template Strings (T-Strings) Implementation

**Priority:** High
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Replace Jinja2 templates with Python 3.14 T-strings (PEP 750) for safer, more powerful templating with runtime validation and structured interpolation.

### User Stories
- As a developer, I want T-strings so I have safer template processing with compile-time validation
- As a maintainer, I want T-strings so I can debug template errors at import time
- As a user, I want consistent template errors so I understand what went wrong

### Acceptance Criteria
- [ ] Create `TemplateEngine` service using T-strings
- [ ] Convert `students.html` to T-string format (`.thtml` extension)
- [ ] Convert `teachers.html` to T-string format
- [ ] Update `SuplovaniZaci` to use `TemplateEngine`
- [ ] Update `SuplovaniUcitele` to use `TemplateEngine`
- [ ] Create T-string templates for error/success notifications
- [ ] Remove Jinja2 dependency if no longer needed
- [ ] All T-string templates validate successfully at import time

### Technical Requirements
- Use `string.Template` with T-string syntax (`t"""..."""`)
- Support for-loops in T-strings via template processor
- Context validation before template rendering
- Fallback to Jinja2 for complex templates if needed

### Dependencies
- Package Structure Restructure (Feature 2)

### Notes
T-strings provide security benefits (no code injection) and better performance than Jinja2.

---

## Feature: Domain Models & Protocols

**Priority:** High
**Complexity:** High
**Effort:** 3-4 hours

### Description
Implement rich domain models using dataclasses with slots and protocol-based interfaces for dependency injection, type safety, and clear contracts between components.

### User Stories
- As a developer, I want domain models so business logic is clear and testable
- As a maintainer, I want protocols so I can mock dependencies in tests
- As a contributor, I want clear interfaces so I understand component contracts

### Acceptance Criteria
- [ ] Create `SubstitutionRecord`, `AbsenceRecord`, `Teacher`, `Period` dataclasses
- [ ] Use `@dataclass(slots=True, frozen=True)` for immutability
- [ ] Create `ResolutionType` and `OutputFormat` enums
- [ ] Define `XMLParser`, `Downloader`, `Exporter`, `FileWatcher` protocols
- [ ] Update existing classes to implement protocols
- [ ] Refactor `SuplovaniBase` to use domain models instead of dicts
- [ ] All protocols have clear method signatures and docstrings
- [ ] Type safety validated by mypy in strict mode

### Technical Requirements
- Domain models in `src/skolaonline/domain/models.py`
- Protocols in `src/skolaonline/core/protocols.py`
- Enums in `src/skolaonline/domain/enums.py`
- All methods on protocols have type hints
- Value objects for domain concepts (Period, Teacher)

### Dependencies
- Package Structure Restructure (Feature 2)

### Notes
Frozen dataclasses prevent bugs through immutability. Protocols enable easy testing and multiple implementations.

---

## Feature: Pydantic Configuration

**Priority:** High
**Complexity:** Medium
**Effort:** 3-4 hours

### Description
Replace scattered configuration (YAML, env, CLI, hardcoded) with unified Pydantic model providing validation, type safety, and single source of truth.

### User Stories
- As a user, I want configuration validation so I get clear error messages for invalid settings
- As a developer, I want typed config so IDE provides autocomplete and type checking
- As a maintainer, I want centralized configuration so I can add settings in one place

### Acceptance Criteria
- [ ] Create `SublovaniConfig` Pydantic model
- [ ] Load config from YAML with Pydantic Settings
- [ ] Support environment variable overrides with `SO_` prefix
- [ ] Validate paths exist and are directories
- [ ] Validate output formats are supported
- [ ] Validate day_end_hour is 1-8 or None
- [ ] Replace existing `Settings` class with Pydantic version
- [ ] All validation errors are clear and actionable

### Technical Requirements
- Use `pydantic-settings` for environment variable support
- Field validators for custom validation logic
- Type hints on all config fields
- Default values for all optional fields
- Auto-create directories for path fields

### Dependencies
- Domain Models & Protocols (Feature 4)
- Package Structure Restructure (Feature 2)

### Notes
Eliminates configuration bugs through validation. Single source of truth simplifies maintenance.

---

## Feature: Service Layer & Repository Pattern

**Priority:** High
**Complexity:** High
**Effort:** 3-4 hours

### Description
Implement service layer for business logic orchestration and repository pattern for data access, providing clean separation of concerns and testability.

### User Stories
- As a developer, I want service layer so business logic is reusable and testable
- As a maintainer, I want repository pattern so I can swap data storage implementations
- As a tester, I want dependency injection so I can mock components easily

### Acceptance Criteria
- [ ] Create `XMLRepository` abstract base class
- [ ] Implement `FileSystemXMLRepository` for file operations
- [ ] Create `XMLParserService` for parsing logic
- [ ] Create `ExportService` for export operations
- [ ] Create `SuplovaniWorkflowService` for full workflow
- [ ] All services use protocol-based dependencies
- [ ] All repository methods have type hints
- [ ] File moves use atomic operations

### Technical Requirements
- Repository in `src/skolaonline/services/repositories.py`
- Services in `src/skolaonline/services/`
- Abstract methods defined in protocols
- Concrete implementations follow Liskov Substitution Principle
- Error handling with custom exceptions

### Dependencies
- Pydantic Configuration (Feature 5)
- Domain Models & Protocols (Feature 4)

### Notes
Repository pattern enables swapping file system for cloud storage in future. Service layer keeps business logic clean.

---

## Feature: Unified CLI with Typer

**Priority:** High
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Create unified command-line interface using Typer framework, replacing multiple script entry points with single CLI supporting subcommands and rich colored output.

### User Stories
- As a user, I want unified CLI so I have one command for all operations
- As a user, I want colored output so commands are easy to read
- As a developer, I want Typer framework so CLI is maintainable and extensible

### Acceptance Criteria
- [ ] Create `src/skolaonline/cli.py` with typer app
- [ ] Implement `download` subcommand (from `so_download.py` and `so_soap.py`)
- [ ] Implement `process` subcommand (existing XML processing)
- [ ] Implement `watch` subcommand (from `suplovani.py`)
- [ ] Implement `record` subcommand (from `so_recorder.py`)
- [ ] Add `--help` for all subcommands
- [ ] Use Rich for colored console output
- [ ] Add progress bars for long operations

### Technical Requirements
- Use `typer` for CLI definition
- Use `rich` for colored output and progress bars
- Type hints on all CLI parameters
- Validation for CLI arguments
- Consistent command naming conventions

### Dependencies
- Service Layer & Repository Pattern (Feature 6)
- Pydantic Configuration (Feature 5)

### Notes
Simplifies user experience. One command (`so-suplovani`) instead of 4 separate scripts.

---

## Feature: Backward Compatibility Wrappers

**Priority:** Critical
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Create wrapper scripts for old command names (`so_download.py`, `so_soap.py`, `suplovani.py`) that delegate to new CLI with deprecation warnings, ensuring seamless migration.

### User Stories
- As an existing user, I want old commands to still work so I don't have to change my workflows immediately
- As a developer, I want deprecation warnings so I know when commands will be removed
- As a maintainer, I want migration path so I can track adoption of new CLI

### Acceptance Criteria
- [ ] Create `wrapped_old_scripts.py` module with deprecation logic
- [ ] Update old scripts to use wrapper with warnings
- [ ] Show clear migration instructions in deprecation warnings
- [ ] Old commands execute successfully (delegate to new CLI)
- [ ] All old commands show deprecation warning
- [ ] Add entry point aliases in pyproject.toml
- [ ] Document deprecation timeline (v2.0 → v3.0)

### Technical Requirements
- Wrapper module with command mapping
- DeprecationWarning for warnings
- Subprocess execution of new CLI
- Clear error messages for missing new CLI
- Optional `--suppress-warnings` and `--force-legacy` flags

### Dependencies
- Unified CLI with Typer (Feature 7)

### Notes
Phase out old commands over 12-18 months. Version 2.5: warnings become errors. Version 3.0: removed.

---

## Feature: Comprehensive Testing Infrastructure

**Priority:** High
**Complexity:** High
**Effort:** 3-4 hours

### Description
Implement comprehensive testing infrastructure including unit tests, integration tests, property-based tests, fixtures, and coverage reporting using pytest ecosystem.

### User Stories
- As a developer, I want comprehensive tests so I can catch bugs early
- As a maintainer, I want coverage reports so I know code is well-tested
- As a contributor, I want fixtures so writing tests is easy

### Acceptance Criteria
- [ ] Create `tests/` directory with proper structure
- [ ] Create `conftest.py` with shared fixtures
- [ ] Implement unit tests for domain models
- [ ] Implement unit tests for services
- [ ] Implement integration tests for full workflows
- [ ] Add property-based tests with hypothesis
- [ ] Achieve 80%+ code coverage
- [ ] All tests pass on Python 3.14

### Technical Requirements
- Use `pytest` for test framework
- Use `pytest-cov` for coverage reporting
- Use `hypothesis` for property-based testing
- Test fixtures in `tests/fixtures/`
- Organize tests by type: `tests/unit/`, `tests/integration/`
- Mock external dependencies (HTTP, file system)

### Dependencies
- Domain Models & Protocols (Feature 4)
- Service Layer & Repository Pattern (Feature 6)

### Notes
Property-based tests catch edge cases unit tests miss. 80% coverage ensures confidence in refactoring.

---

## Feature: Pre-commit Hooks & Code Quality

**Priority:** High
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Implement pre-commit hooks for automated code quality enforcement including formatting, linting, type checking, and security scanning before commits.

### User Stories
- As a developer, I want pre-commit hooks so code quality is enforced automatically
- As a maintainer, I want automated formatting so code style is consistent
- As a team member, I want type checking before commits so type errors are caught early

### Acceptance Criteria
- [ ] Create `.pre-commit-config.yaml` with all hooks
- [ ] Configure `black` for code formatting
- [ ] Configure `isort` for import sorting
- [ ] Configure `pylint` for static analysis
- [ ] Configure `mypy` for type checking (strict mode)
- [ ] Configure `ruff` for fast linting
- [ ] Configure `bandit` for security scanning
- [ ] Create `.isort.cfg` and `.black.toml` configs
- [ ] All hooks run successfully on all files

### Technical Requirements
- Use `pre-commit` framework
- Hooks: black, isort, pylint, mypy, ruff, bandit, pytest
- Cache hooks for performance
- Run only on changed files
- `.pylintrc` used by pylint hook

### Dependencies
- Python 3.14 Migration (Feature 1)
- Comprehensive Testing (Feature 9)

### Notes
Automates code quality enforcement. Prevents bad code from entering repository.

---

## Feature: Performance Optimizations

**Priority:** Medium
**Complexity:** Medium
**Effort:** 2-3 hours

### Description
Implement performance optimizations leveraging Python 3.14 capabilities including Zstandard compression, incremental garbage collection, and enhanced pathlib operations.

### User Stories
- As a user, I want faster compression so archives are smaller and created quicker
- As a maintainer, I want optimized garbage collection so long-running processes are efficient
- As a developer, I want modern pathlib operations so code is cleaner and faster

### Acceptance Criteria
- [ ] Add Zstandard (zstd) compression for XML archives
- [ ] Implement GC optimization for long-running file watcher
- [ ] Use enhanced pathlib methods (3.14 features)
- [ ] Add atomic file operations to prevent corruption
- [ ] Benchmark performance improvements (before/after)
- [ ] Document performance gains

### Technical Requirements
- Use `compression.zstd` module (Python 3.14)
- Use `gc.disable()` and `gc.enable()` for GC optimization
- Use atomic write operations (Path.replace)
- Use pathlib improvements (3.14)

### Dependencies
- Service Layer & Repository Pattern (Feature 6)

### Notes
Zstd is 20-30% faster than gzip with similar/better compression. Incremental GC reduces pause times.

---

## Feature: Modern Packaging with pyproject.toml

**Priority:** High
**Complexity:** Low
**Effort:** 2-3 hours

### Description
Replace `requirements.txt` and setup.py with modern `pyproject.toml` using PEP 621 specification, providing proper dependency management and installation.

### User Stories
- As a user, I want pip installable package so installation is standard
- As a developer, I want pyproject.toml so dependency management is modern
- As a maintainer, I want proper package metadata so distribution is standard

### Acceptance Criteria
- [ ] Create `pyproject.toml` with all metadata
- [ ] Replace `requirements.txt` with pyproject.toml dependencies
- [ ] Configure build system (hatchling)
- [ ] Add entry points for all CLI commands
- [ ] Configure development dependencies
- [ ] Add scripts for `so-suplovani`, `so-download`, etc.
- [ ] Package installs successfully with `pip install -e .`
- [ ] All entry points work from command line

### Technical Requirements
- Use `[build-system]` with hatchling
- Use `[project]` for metadata and dependencies
- Use `[project.optional-dependencies]` for dev deps
- Use `[project.scripts]` for entry points
- Configure mypy, ruff, pytest, pylint, coverage in tool sections
- Delete `requirements.txt` after migration

### Dependencies
- All previous features (aggregates configuration)

### Notes
Standard Python packaging. Makes distribution to PyPI trivial. Aligns with modern Python ecosystem.

---

## Feature: CI/CD Updates for Python 3.14

**Priority:** High
**Complexity:** Low
**Effort:** 1-2 hours

### Description
Update GitHub Actions workflows to test on Python 3.14, run pre-commit hooks in CI, and add coverage reporting with Codecov integration.

### User Stories
- As a maintainer, I want CI testing on Python 3.14 so new code works
- As a developer, I want pre-commit checks in CI so PRs are quality-assured
- As a team member, I want coverage reports so I know test coverage

### Acceptance Criteria
- [ ] Update `.github/workflows/test.yml` to include Python 3.14
- [ ] Add pre-commit run step in CI
- [ ] Add pytest with coverage step
- [ ] Configure Codecov upload
- [ ] Update `.github/workflows/pylint.yml` for Python 3.14
- [ ] All CI workflows pass on Python 3.14
- [ ] Coverage reports generated and uploaded

### Technical Requirements
- Use `actions/setup-python@v5`
- Test matrix includes Python 3.14
- Run `pre-commit run --all-files`
- Run `pytest --cov` with xml output
- Upload coverage to Codecov

### Dependencies
- Modern Packaging with pyproject.toml (Feature 12)
- Pre-commit Hooks & Code Quality (Feature 10)
- Comprehensive Testing (Feature 9)

### Notes
Ensures code quality gate on all PRs. Coverage reports track test quality over time.

---

## Feature: Documentation & Migration Guide

**Priority:** Medium
**Complexity:** Low
**Effort:** 2-3 hours

### Description
Create comprehensive documentation including architecture overview, migration guide for users, contribution guidelines, and API documentation.

### User Stories
- As a user, I want migration guide so I can transition from old to new CLI
- As a contributor, I want architecture docs so I understand codebase
- As a developer, I want contribution guide so I can contribute effectively

### Acceptance Criteria
- [ ] Create `docs/architecture.md` with system overview
- [ ] Create `docs/MIGRATION.md` with step-by-step migration guide
- [ ] Create `docs/contributing.md` with contribution guidelines
- [ ] Update `README.md` with new installation instructions
- [ ] Document all CLI commands with examples
- [ ] Document all configuration options
- [ ] Add deprecation timeline documentation
- [ ] All documentation is clear and accurate

### Technical Requirements
- Architecture diagrams in Markdown
- Code examples for all CLI commands
- Before/after comparisons for migration
- Clear deprecation timeline (v2.0 → v3.0)
- Contribution guidelines including setup and testing

### Dependencies
- All previous features (comprehensive documentation)

### Notes
Good documentation reduces support burden. Migration guide ensures smooth user transition.

---

## Feature: Validation & Cleanup

**Priority:** Critical
**Complexity:** Low
**Effort:** 1-2 hours

### Description
Final validation phase ensuring all features work together, tests pass, code quality is high, and old files are cleaned up.

### User Stories
- As a maintainer, I want validation so modernization is successful
- As a user, I want all tests passing so I can trust the software
- As a developer, I want cleanup so codebase is clean

### Acceptance Criteria
- [ ] Run all unit tests - 100% pass rate
- [ ] Run all integration tests - 100% pass rate
- [ ] Run mypy strict mode - no errors
- [ ] Run pre-commit hooks on all files - all pass
- [ ] Test all CLI commands - all work
- [ ] Test old wrapper commands - all work with warnings
- [ ] Archive old scripts to `scripts/legacy/`
- [ ] Update `.gitignore` for new structure
- [ ] Final commit with comprehensive message

### Technical Requirements
- `pytest tests/unit/ -v` passes
- `pytest tests/integration/ -v` passes
- `mypy src/ --strict` passes
- `pre-commit run --all-files` passes
- All CLI commands execute successfully
- Old wrappers show deprecation warnings

### Dependencies
- All previous features (validation of complete modernization)

### Notes
This is final gate before release. Ensures no regressions introduced.

---

## Summary

### Total Features: 14
### Total Estimated Effort: 32-45 hours

### Feature Dependencies Graph:
```
Feature 1 (Python 3.14)
    ↓
Feature 2 (Package Restructure)
    ↓
    ├─→ Feature 3 (T-Strings)
    ├─→ Feature 4 (Domain Models)
    │       ↓
    │   Feature 5 (Pydantic Config)
    │       ↓
    │   Feature 6 (Service Layer)
    │       ↓
    │   Feature 7 (Unified CLI)
    │       ↓
    │   Feature 8 (Backward Compatibility)
    │       ↓
    │   Feature 9 (Testing)
    │   Feature 10 (Pre-commit Hooks)
    │   Feature 11 (Performance)
    └─→ Feature 12 (pyproject.toml)
            ↓
            Feature 13 (CI/CD)
            Feature 14 (Documentation)
            ↓
            Feature 15 (Validation)
```

### Risk Assessment:
- **Critical Risk:** Breaking changes in package restructure and CLI
  - **Mitigation:** Backward compatibility wrappers, clear migration guide
- **Medium Risk:** Python 3.14 dependency
  - **Mitigation:** Clear documentation, Docker images
- **Low Risk:** Pre-commit hooks slowing down commits
  - **Mitigation:** Cached hooks, run on changed files only

### Rollback Plan:
If modernization fails:
1. Create release branch from pre-modernization commit
2. Tag as v1.9.0 (last stable version)
3. Continue maintenance on v1.x branch
4. Retry modernization after lessons learned

### Success Criteria:
- ✅ All features completed and tested
- ✅ 80%+ code coverage
- ✅ All pre-commit hooks passing
- ✅ Zero regressions in functionality
- ✅ Documentation complete and accurate
- ✅ Old commands still work with warnings
- ✅ Performance improvements verified
