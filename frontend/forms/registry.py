"""
Created on 2026-03-30

@author: wf
"""

import os
from pathlib import Path
from typing import Dict, Optional

from frontend.forms.form_field import FormDefinition

DEFAULT_FORMS_DIR = os.path.expanduser("~/.wikicms/forms")

# Built-in example forms shipped with the package
_BUILTIN_FORMS_DIR = Path(__file__).parent.parent / "resources" / "forms"


class FormRegistry:
    """
    Singleton registry for FormDefinition instances.
    Class methods operate on the single shared instance.

    On first use the registry is populated with:
    1. Built-in example forms from frontend/resources/forms/*.yaml
    2. User-defined forms from ~/.wikicms/forms/*.yaml (override built-ins
       if names collide)
    """

    _instance: Optional["FormRegistry"] = None

    def __init__(self):
        self._forms: Dict[str, FormDefinition] = {}

    @classmethod
    def _load_dir(cls, forms_dir: str) -> None:
        """
        Load all *.yaml files from *forms_dir* into the current singleton.

        Args:
            forms_dir(str): path to directory containing form YAML files
        """
        if os.path.isdir(forms_dir):
            for fname in sorted(os.listdir(forms_dir)):
                if fname.endswith(".yaml"):
                    yaml_path = os.path.join(forms_dir, fname)
                    FormRegistry.register_from_yaml(yaml_path)

    @classmethod
    def of_forms_dir(cls, forms_dir: str = None) -> "FormRegistry":
        """
        Create a new FormRegistry loaded from *forms_dir* (and built-ins).

        Built-in forms are loaded first; user forms loaded second so they can
        override built-ins by name.

        Args:
            forms_dir(str): path to user form YAML directory
                            (default: ~/.wikicms/forms)

        Returns:
            FormRegistry: the populated singleton registry
        """
        if forms_dir is None:
            forms_dir = DEFAULT_FORMS_DIR
        registry = FormRegistry()
        cls._instance = registry
        # 1. Load built-in example forms
        cls._load_dir(str(_BUILTIN_FORMS_DIR))
        # 2. Load user-defined forms (may override built-ins)
        cls._load_dir(forms_dir)
        return registry

    @classmethod
    def instance(cls) -> "FormRegistry":
        """
        Return the singleton FormRegistry instance, creating it if needed.
        """
        if cls._instance is None:
            cls._instance = cls.of_forms_dir()
        return cls._instance

    @classmethod
    def register(cls, form_def: FormDefinition) -> None:
        """
        Register a FormDefinition by its name.

        Args:
            form_def(FormDefinition): the form definition to register
        """
        cls.instance()._forms[form_def.name] = form_def

    @classmethod
    def register_from_yaml(cls, yaml_path: str) -> FormDefinition:
        """
        Load a FormDefinition from a YAML file and register it.

        Args:
            yaml_path(str): path to the YAML file

        Returns:
            FormDefinition: the loaded and registered form definition
        """
        form_def = FormDefinition.load_from_yaml_file(yaml_path)  # @UndefinedVariable
        cls.register(form_def)
        return form_def

    @classmethod
    def get(cls, name: str) -> Optional[FormDefinition]:
        """
        Retrieve a registered FormDefinition by name.

        Args:
            name(str): the form name

        Returns:
            FormDefinition or None if not found
        """
        form_def = cls.instance()._forms.get(name)
        return form_def
