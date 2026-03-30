"""
Created on 2026-03-30

@author: wf
"""

import hashlib
import secrets
from typing import Dict, List

from frontend.forms.form_field import FormDefinition


class FormHandler:
    """
    Handles POST validation for a form definition.
    Checks required fields, validates captcha and postToken.
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
        cls, form_def: FormDefinition, post_data: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """
        Validate POST data against the form definition.

        Args:
            form_def(FormDefinition): the form definition
            post_data(dict): POST data keyed by field name

        Returns:
            dict: errors keyed by field name; empty dict means valid
        """
        errors: Dict[str, List[str]] = {}

        for field in form_def.fields:
            if field.required:
                val = post_data.get(field.name, "").strip()
                if not val:
                    msg = (
                        field.error_msg
                        or f"{field.label or field.name} ist erforderlich."
                    )
                    errors.setdefault(field.name, []).append(msg)

        # captcha validation: expected hidden field holds the expected answer
        captcha_answer = post_data.get("captcha_answer", "").strip()
        captcha_expected = post_data.get("captcha_expected", "").strip()
        if captcha_expected:
            if captcha_answer.lower() != captcha_expected.lower():
                errors.setdefault("captcha_answer", []).append(
                    "Captcha-Antwort ist nicht korrekt."
                )

        # postToken validation
        post_token = post_data.get("postToken", "").strip()
        token_expected = post_data.get("postToken_expected", "").strip()
        if token_expected:
            if post_token != token_expected:
                errors.setdefault("postToken", []).append(
                    "Ungültiges Formular-Token. Bitte Seite neu laden."
                )

        return errors
