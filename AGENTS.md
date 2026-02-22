# AGENTS.md - Agent Coding Guidelines for pyWikiCMS

This file provides guidelines for agentic coding agents working on this repository.

## Important Rules

**CRITICAL: NEVER EVER DO ANY ACTION READING, MODIFYING OR RUNNING without explaing the plan
Each set of intended actions needs to be explained in the format:
I understood that <YOUR ANALYSIS> so that i plan to <GOALS YOU PURSUE> by <ACTIONS TO BE CONFIRMED> confirm with go!
YOU WILL NEVER PROCEED WITH OUT POSITIVE CONFIRMATION by go!

## Project Overview

pyWikiCMS is a Python-based MediaWiki Content Management System frontend. It consists of:
- `frontend/` - Web UI components (FastAPI-based)
- `site/` - Site-specific configuration
- `tests/` - Unit tests using unittest

Requires Python 3.10+.

---

## Build, Lint, and Test Commands

### Installation
```bash
pip install -e .
# or: scripts/install
```

### Running Tests

**Run all tests with unittest discover (default):**
```bash
python3 -m unittest discover
# or: scripts/test
```

**Run tests with green:**
```bash
scripts/test -g
# or: green tests -s 1
```

**Run tests module-by-module:**
```bash
scripts/test -m
```

**Run tests with tox:**
```bash
scripts/test -t
```

**Run a single test file:**
```bash
python -m unittest tests/test_wikicms.py
```

**Run a specific test method:**
```bash
python -m unittest tests.test_wikicms.TestWikiCMS.testWikiCMS
```

### Code Formatting

**Format and sort imports:**
```bash
scripts/blackisort
```
This runs `isort` then `black` on `tests/`, `frontend/`, and `site/` directories.

### Running the Application

**Start the web server:**
```bash
python -m frontend.cmsmain
# or: wikicms
```

**Other CLI commands (provided by MediaWikiServerTools):**

```bash
tsite   # mwstools_backend.tsite:main
sqlbackup  # mwstools_backend.sql_backup:main
cronbackup # mwstools_backend.cron_backup:main
```

---

## Code Style Guidelines

### Imports

Order imports as follows (enforced by isort):
1. Standard library
2. Third-party packages
3. Local application imports

Use relative imports within the project:
```python
from mwstools_backend.site import FrontendSite
from frontend.frame import HtmlFrame
```

### Formatting

- **Line length**: Follow black's default (88 characters)
- **Strings**: Use f-strings for string interpolation
- **Indentation**: 4 spaces (no tabs)

### Type Hints

Use type hints for function signatures and variables:
```python
def getContent(self, pagePath: str) -> tuple[str, Optional[str], Optional[str]]:
    # ...
```

Common types used: `str`, `int`, `bool`, `List`, `Dict`, `Optional`, `Any`

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `WikiFrontend`, `Site`)
- **Functions/methods**: `snake_case` (e.g., `get_content()`, `fix_images_and_videos()`)
- **Variables**: `snake_case` (e.g., `page_title`, `filter_keys`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Private methods**: prefix with underscore (e.g., `_resolve_ip()`)

### Docstrings

Use docstrings for all public classes and functions:
```python
def extract_site_and_path(path: str):
    """
    Splits the given path into the site component and the remaining path.

    Parameters:
        path (str): The complete path to split.

    Returns:
        tuple: A tuple where the first element is the site and the second
               element is the subsequent path.
    """
```

### Error Handling

- Use try/except blocks with specific exception types when possible
- Include meaningful error messages
- Example pattern from codebase:
```python
try:
    content = self.wiki.getHtml(pageTitle)
except Exception as e:
    error = self.errMsg(e)
```

### Logging

Use the logging module:
```python
import logging
self.logger = logging.getLogger(self.__class__.__name__)
self.logger.debug("message")
```

### Class Structure

- Classes should inherit from `object` or other base classes
- Use dataclasses for simple data containers:
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Site:
    name: str
    container: Optional[str] = None
    ip: str = field(default="?", init=False)
```

### Constants and Configuration

- Store configuration in class attributes with type annotations
- Use `field(default=..., init=False)` for computed/non-init fields

### Testing

- Test classes inherit from `Basetest` (from basemkit)
- Test methods should start with `test_`
- Use assertions: `self.assertTrue()`, `self.assertEqual()`
- Debug output with `print()` using f-strings

### File Organization

```
pyWikiCMS/
├── frontend/          # Web UI code
│   ├── __init__.py
│   ├── wikicms.py
│   ├── webserver.py
│   └── ...
├── tests/            # Unit tests
│   ├── test_wikicms.py
│   └── ...
├── scripts/          # Build/utility scripts
│   ├── blackisort
│   ├── test
│   └── install
├── site/             # Site-specific configuration
├── docs/             # Documentation
└── pyproject.toml
```

**Note:** Backend functionality is provided by the `MediaWikiServerTools` package (import modules as `mwstools_backend.*`).

### Dependencies

Key dependencies (see pyproject.toml):
- `pybasemkit` - Base utilities
- `ngwidgets` - NiceGUI widgets
- `pyLodStorage` - LOD storage
- `py-3rdparty-mediawiki` - MediaWiki client
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML processing
- `fastapi` - Web framework

---

## CI/CD

GitHub Actions workflow: `.github/workflows/build.yml`
- Runs on Python 3.10
- Installs dependencies via `scripts/install`
- Runs tests via `scripts/test`

---

## Additional Notes

- Version is managed via hatchling in `frontend/__init__.py`
- Package uses flit/hatchling build system
- Follow existing code patterns when extending functionality
