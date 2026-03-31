"""
Created on 2026-03-31

@author: wf
"""

import os
from pathlib import Path
from typing import Dict, List


# Built-in resources shipped with the package
_BUILTIN_DIR = Path(__file__).parent / "resources"

# User-level override directory
_USER_DIR = Path(os.path.expanduser("~/.wikicms"))


class ResourceLoader:
    """
    Loads CSS and JS resource snippets from the built-in resource directory
    and an optional user override directory.

    Resolution order per resource type (css, js):
      1. Built-in: frontend/resources/{kind}/*.{kind}
      2. User:     ~/.wikicms/{kind}/*.{kind}

    If a user file has the same name as a built-in file, the user file
    wins (override).  Files are sorted alphabetically so load order is
    deterministic.
    """

    def __init__(
        self,
        builtin_dir: Path = _BUILTIN_DIR,
        user_dir: Path = _USER_DIR,
    ):
        self.builtin_dir = builtin_dir
        self.user_dir = user_dir
        self._cache: Dict[str, str] = {}

    def _collect_files(self, kind: str) -> List[Path]:
        """
        Collect resource files for *kind* (``"css"`` or ``"js"``).

        Built-in files are loaded first; user files override by filename.

        Args:
            kind(str): resource type — ``"css"`` or ``"js"``

        Returns:
            list[Path]: ordered list of file paths to include
        """
        builtin_path = self.builtin_dir / kind
        user_path = self.user_dir / kind

        # Collect built-in files keyed by filename
        files_by_name: Dict[str, Path] = {}
        if builtin_path.is_dir():
            for f in sorted(builtin_path.iterdir()):
                if f.suffix == f".{kind}" or f.name.endswith(f".{kind}"):
                    files_by_name[f.name] = f

        # User files override built-ins by name, or add new ones
        if user_path.is_dir():
            for f in sorted(user_path.iterdir()):
                if f.suffix == f".{kind}" or f.name.endswith(f".{kind}"):
                    files_by_name[f.name] = f

        # Return in sorted filename order
        result = [files_by_name[name] for name in sorted(files_by_name)]
        return result

    def _load_kind(self, kind: str) -> str:
        """
        Load and concatenate all resource files of *kind*.

        Results are cached after first call.

        Args:
            kind(str): resource type — ``"css"`` or ``"js"``

        Returns:
            str: concatenated file contents
        """
        if kind not in self._cache:
            parts = []
            for path in self._collect_files(kind):
                content = path.read_text(encoding="utf-8")
                parts.append(content)
            self._cache[kind] = "\n".join(parts)
        result = self._cache[kind]
        return result

    def css(self) -> str:
        """
        Return all CSS resource content (link tags, inline styles).

        Returns:
            str: concatenated CSS snippets
        """
        result = self._load_kind("css")
        return result

    def js(self) -> str:
        """
        Return all JS resource content (script tags, inline scripts).

        Returns:
            str: concatenated JS snippets
        """
        result = self._load_kind("js")
        return result

    def clear_cache(self):
        """
        Clear the cached resources so they are reloaded on next access.
        """
        self._cache.clear()
