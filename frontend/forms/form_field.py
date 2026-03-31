"""
Created on 2026-03-30

@author: wf
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from basemkit.yamlable import lod_storable


# Type alias: a translatable string is either a plain str or a
# language-keyed dict, e.g. {"en": "Name", "de": "Name", "fr": "Nom"}.
I18nStr = Optional[Union[str, Dict[str, str]]]


class I18n:
    """
    Internationalization helper class.
    """

    @staticmethod
    def resolve(value: I18nStr, lang: str = "en") -> str:
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
            resolved = ""
        elif isinstance(value, dict):
            resolved = value.get(lang) or value.get("en")
            if resolved is None and value:
                resolved = next(iter(value.values()))
            resolved = resolved or ""
        else:
            resolved = value
        return resolved


def resolve_i18n(value: I18nStr, lang: str = "en") -> str:
    """Backward compatible alias for I18n.resolve()"""
    resolved = I18n.resolve(value, lang)
    return resolved


@dataclass
class HtmlElement:
    """
    Base class for HTML elements with common attributes.

    Uses plain @dataclass (not @lod_storable) because it serves as a
    base class — @lod_storable wraps with YamlAble which would cause
    MRO conflicts in subclasses that also use @lod_storable.
    """

    css_class: str = ""  # e.g. "form-control selectpicker"
    size: str = ""  # xs, sm, md, lg


@lod_storable
class FormLabel(HtmlElement):
    """
    Label element with i18n support for form fields.

    Defined in YAML as an object with text and optional css_class/size::

        label:
          text:
            en: "Name"
            de: "Name"
          css_class: "bitplanorange"
          size: "md"
    """

    text: I18nStr = ""  # the label text


@lod_storable
class FormField(HtmlElement):
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

    name: str = ""  # required but defaults to empty for compatibility
    field_type: str = "text"  # text | textarea | select | hidden | email
    label: FormLabel = None  # FormLabel object with text, css_class, size
    placeholder: I18nStr = None
    glyphicon: Optional[str] = None
    required: bool = False
    error_msg: I18nStr = None
    value: Optional[str] = None  # for hidden fields / pre-filled defaults
    choices: Optional[List[str]] = None  # for select fields
    placeholder_choice: I18nStr = None  # e.g. "Bitte wählen" for select fields
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
    submit_label: I18nStr = None  # defaults to {"en": "Send", "de": "Absenden"}
    submit_glyphicon: Optional[str] = None
    success_message: I18nStr = None

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
