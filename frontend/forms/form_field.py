"""
Created on 2026-03-30

@author: wf
"""

from typing import Any, Dict, List, Optional, Union

from basemkit.yamlable import lod_storable

# Type alias: a translatable string is either a plain str or a
# language-keyed dict, e.g. {"en": "Name", "de": "Name", "fr": "Nom"}.
I18nStr = Optional[Union[str, Dict[str, str]]]


def resolve_i18n(value: I18nStr, lang: str = "en") -> str:
    """
    Resolve a possibly-multilingual value to a plain string.

    If *value* is a dict, return the entry for *lang*, falling back to "en",
    then to the first available value.  If *value* is already a str (or None),
    return it as-is (empty string for None).

    Args:
        value(I18nStr): a plain string, a language-keyed dict, or None
        lang(str): the desired language code (default "en")

    Returns:
        str: the resolved string for the requested language
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        resolved = value.get(lang) or value.get("en")
        if resolved is None and value:
            resolved = next(iter(value.values()))
        return resolved or ""
    return value


@lod_storable
class FormField:
    """
    A single field in a form definition.

    Translatable fields (label, placeholder, error_msg) accept either a plain
    string or a language-keyed dict::

        label:
          en: "Name"
          de: "Name"
          fr: "Nom"

    The *validators* list contains WTForms validator descriptors, e.g.::

        validators:
          - type: DataRequired
          - type: Length
            min: 2
            max: 100
          - type: Email
    """

    name: str
    field_type: str  # text | textarea | select | hidden | email
    label: Any = None  # I18nStr
    placeholder: Any = None  # I18nStr
    glyphicon: Optional[str] = None
    required: bool = False
    error_msg: Any = None  # I18nStr
    value: Optional[str] = None  # for hidden fields / pre-filled defaults
    choices: Optional[List[str]] = None  # for select fields
    validators: Optional[List[Dict[str, Any]]] = None  # WTForms validator descriptors


@lod_storable
class FormDefinition:
    """
    A complete form definition with all fields and metadata.

    Translatable fields (legend, submit_label, success_message) accept either
    a plain string or a language-keyed dict.
    """

    name: str
    legend: Any  # I18nStr — required, no default
    fields: List[FormField]
    action: str = ""
    submit_label: Any = None  # I18nStr; defaults to {"en": "Send", "de": "Absenden"}
    submit_glyphicon: Optional[str] = None
    success_message: Any = None  # I18nStr

    def resolved_submit_label(self, lang: str = "en") -> str:
        """
        Return the submit button label for *lang*, falling back to built-in defaults.

        Args:
            lang(str): language code

        Returns:
            str: resolved submit label
        """
        _defaults: Dict[str, str] = {
            "en": "Send",
            "de": "Absenden",
            "fr": "Envoyer",
            "es": "Enviar",
            "it": "Invia",
            "nl": "Verzenden",
        }
        label = resolve_i18n(self.submit_label, lang)
        if not label:
            label = _defaults.get(lang) or _defaults["en"]
        return label
