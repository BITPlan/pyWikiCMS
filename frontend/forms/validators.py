"""
Created on 2026-03-30

@author: wf

Maps YAML validator descriptor dicts to WTForms validator instances and
runs WTForms-based validation against raw POST data.
"""

from typing import Any, Dict, List, Optional

import wtforms.validators as wv
from wtforms.validators import StopValidation

from frontend.forms.form_field import FormDefinition, FormField, resolve_i18n

# Map of YAML type names to WTForms validator classes
_VALIDATOR_MAP: Dict[str, Any] = {
    "DataRequired": wv.DataRequired,
    "InputRequired": wv.InputRequired,
    "Optional": wv.Optional,
    "Email": wv.Email,
    "Length": wv.Length,
    "NumberRange": wv.NumberRange,
    "Regexp": wv.Regexp,
    "URL": wv.URL,
    "IPAddress": wv.IPAddress,
    "MacAddress": wv.MacAddress,
    "UUID": wv.UUID,
    "AnyOf": wv.AnyOf,
    "NoneOf": wv.NoneOf,
}


def build_wtforms_validators(field: FormField, lang: str = "en") -> List[Any]:
    """
    Build a list of WTForms validator instances from a FormField's
    *validators* descriptor list.

    Descriptor format (YAML / dict)::

        validators:
          - type: DataRequired
            message: "Custom error message"   # optional
          - type: Length
            min: 2
            max: 100
          - type: Email

    Unknown *type* values are silently skipped.

    Args:
        field(FormField): the field whose validator descriptors to build
        lang(str): language code used to resolve i18n error messages

    Returns:
        list: WTForms validator instances ready for use
    """
    result = []
    if not field.validators:
        # fall back: if field is required but has no descriptor, add DataRequired
        if field.required:
            msg = resolve_i18n(field.error_msg, lang) or None
            result.append(wv.DataRequired(message=msg))
        return result

    for descriptor in field.validators:
        vtype = descriptor.get("type")
        cls = _VALIDATOR_MAP.get(vtype)
        if cls is None:
            continue
        kwargs: Dict[str, Any] = {k: v for k, v in descriptor.items() if k != "type"}
        # resolve i18n message if present
        if "message" in kwargs:
            kwargs["message"] = resolve_i18n(kwargs["message"], lang) or None
        # for DataRequired / InputRequired: use field.error_msg as fallback message
        if vtype in ("DataRequired", "InputRequired") and "message" not in kwargs:
            msg = resolve_i18n(field.error_msg, lang)
            if msg:
                kwargs["message"] = msg
        result.append(cls(**kwargs))

    return result


def validate_with_wtforms(
    form_def: FormDefinition,
    post_data: Dict[str, str],
    lang: str = "en",
) -> Dict[str, List[str]]:
    """
    Validate POST data using WTForms validators declared in the form definition.

    This replaces the hand-rolled required-field checking in FormHandler with
    proper WTForms validator execution.  Token and captcha checks remain in
    FormHandler.validate() so the two can be composed.

    Args:
        form_def(FormDefinition): the form definition carrying validator descriptors
        post_data(dict): POST data keyed by field name
        lang(str): language code for i18n error messages

    Returns:
        dict: errors keyed by field name; empty dict means all fields passed
    """
    errors: Dict[str, List[str]] = {}

    for field in form_def.fields:
        if field.field_type == "hidden":
            continue
        validators = build_wtforms_validators(field, lang)
        if not validators:
            continue

        raw_value = post_data.get(field.name, "")

        for validator in validators:
            try:
                # WTForms validators expect (form, field) but we call them with
                # a lightweight shim that exposes only .data and .errors
                _run_validator(validator, raw_value, field, errors)
            except StopValidation:
                # StopValidation halts the chain for this field
                break
            except Exception:
                # safety net: skip broken validators
                pass

    return errors


class _FieldShim:
    """
    Minimal stand-in for a WTForms BoundField so validators can run without
    a real WTForms Form instance.
    """

    def __init__(self, data: str):
        self.data = data
        self.errors: List[str] = []

    def gettext(self, string: str) -> str:
        return string

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return singular if n == 1 else plural


def _run_validator(
    validator: Any,
    raw_value: str,
    field: FormField,
    errors: Dict[str, List[str]],
) -> None:
    """
    Run a single WTForms validator against *raw_value*.

    ValidationError messages are collected into *errors[field.name]*.

    Args:
        validator: a WTForms validator instance
        raw_value(str): the raw string value from POST data
        field(FormField): the form field definition (for field.name)
        errors(dict): mutable errors dict to append to
    """
    shim = _FieldShim(raw_value)
    try:
        validator(None, shim)
    except StopValidation as exc:
        # StopValidation with a message means: fail and stop further validators
        if str(exc):
            errors.setdefault(field.name, []).append(str(exc))
        # re-raise as a sentinel so the caller's loop can stop for this field
        raise
    except wv.ValidationError as exc:
        errors.setdefault(field.name, []).append(str(exc))
