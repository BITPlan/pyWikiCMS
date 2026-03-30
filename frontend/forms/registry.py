"""
Created on 2026-03-30

@author: wf
"""

from typing import Dict, Optional
import os
from frontend.forms.form_field import FormDefinition

DEFAULT_FORMS_DIR = os.path.expanduser("~/.wikicms/forms")


class FormRegistry:
    """
    Singleton registry for FormDefinition instances.
    Class methods operate on the single shared instance.
    """

    _instance: Optional["FormRegistry"] = None

    def __init__(self):
        self._forms: Dict[str, FormDefinition] = {}

    @classmethod
    def of_forms_dir(cls, forms_dir: str = None) -> "FormRegistry":
        """
        Load all *.yaml files from forms_dir into the FormRegistry.

        Args:
            forms_dir(str): path to directory containing form YAML files

        Returns:
            FormRegistry: the populated singleton registry
        """
        if forms_dir is None:
            forms_dir = DEFAULT_FORMS_DIR
        registry = FormRegistry()
        cls._instance = registry
        if os.path.isdir(forms_dir):
            for fname in sorted(os.listdir(forms_dir)):
                if fname.endswith(".yaml"):
                    yaml_path = os.path.join(forms_dir, fname)
                    FormRegistry.register_from_yaml(yaml_path)
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
