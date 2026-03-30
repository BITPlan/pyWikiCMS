"""
Created on 2026-03-30

@author: wf
"""

from typing import Dict, Optional

from frontend.forms.form_field import FormDefinition


class FormRegistry:
    """
    Singleton registry for FormDefinition instances.
    Class methods operate on the single shared instance.
    """

    _instance: Optional["FormRegistry"] = None

    def __init__(self):
        self._forms: Dict[str, FormDefinition] = {}

    @classmethod
    def instance(cls) -> "FormRegistry":
        """
        Return the singleton FormRegistry instance, creating it if needed.
        """
        if cls._instance is None:
            cls._instance = cls()
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
        form_def = FormDefinition.load_from_yaml_file(yaml_path)
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
        return cls.instance()._forms.get(name)
