"""
Created on 2026-03-30

@author: wf
"""

import secrets
from typing import Dict, List

from frontend.forms.form_field import FormDefinition, resolve_i18n
from frontend.forms.validators import validate_with_wtforms

# Built-in i18n messages for token/captcha errors.
# Extend with more languages as needed.
_CAPTCHA_ERROR: Dict[str, str] = {
    "en": "The captcha answer is incorrect.",
    "de": "Die Captcha-Antwort ist nicht korrekt.",
    "fr": "La réponse au captcha est incorrecte.",
    "es": "La respuesta del captcha es incorrecta.",
    "it": "La risposta al captcha non è corretta.",
    "nl": "Het captcha-antwoord is onjuist.",
}

_TOKEN_ERROR: Dict[str, str] = {
    "en": "Invalid form token. Please reload the page.",
    "de": "Ungültiges Formular-Token. Bitte Seite neu laden.",
    "fr": "Jeton de formulaire invalide. Veuillez recharger la page.",
    "es": "Token de formulario inválido. Por favor, recargue la página.",
    "it": "Token del modulo non valido. Si prega di ricaricare la pagina.",
    "nl": "Ongeldig formuliertoken. Laad de pagina opnieuw.",
}


def _t(msg_map: Dict[str, str], lang: str) -> str:
    """Return the localised message, falling back to English."""
    return msg_map.get(lang) or msg_map["en"]


class FormHandler:
    """
    Handles POST validation for a form definition.

    Uses WTForms validators declared in the field definitions for field-level
    validation (via validate_with_wtforms), and additionally validates the
    optional captcha and postToken hidden fields.
    """

    @classmethod
    def generate_token(cls) -> str:
        """
        Generate a new postToken.

        Returns:
            str: a secure random hex token
        """
        return secrets.token_hex(16)

    @classmethod
    def validate(
        cls,
        form_def: FormDefinition,
        post_data: Dict[str, str],
        lang: str = "en",
    ) -> Dict[str, List[str]]:
        """
        Validate POST data against the form definition.

        Field-level validation is delegated to WTForms validators declared in
        the form definition.  Token and captcha checks are applied on top.

        Args:
            form_def(FormDefinition): the form definition
            post_data(dict): POST data keyed by field name
            lang(str): language code for i18n error messages (default "en")

        Returns:
            dict: errors keyed by field name; empty dict means valid
        """
        errors: Dict[str, List[str]] = validate_with_wtforms(form_def, post_data, lang)

        # captcha validation: captcha_expected hidden field holds expected answer
        captcha_answer = post_data.get("captcha_answer", "").strip()
        captcha_expected = post_data.get("captcha_expected", "").strip()
        if captcha_expected:
            if captcha_answer.lower() != captcha_expected.lower():
                errors.setdefault("captcha_answer", []).append(_t(_CAPTCHA_ERROR, lang))

        # postToken validation
        post_token = post_data.get("postToken", "").strip()
        token_expected = post_data.get("postToken_expected", "").strip()
        if token_expected:
            if post_token != token_expected:
                errors.setdefault("postToken", []).append(_t(_TOKEN_ERROR, lang))

        return errors
