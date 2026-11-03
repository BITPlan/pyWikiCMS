"""
Created on 2026-11-03

@author: wf

the mail action of a form: the wiki sends the submission to a wiki user
via the MediaWiki emailuser API, so the wiki's own mail configuration is the
only mail configuration, see https://github.com/BITPlan/pyWikiCMS/issues/41
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from frontend.forms.form_field import FormDefinition, I18n


@dataclass
class FormPost:
    """
    the state of a submitted form while its page is rendered again:
    the values to keep, the errors per field or the message of a valid submission
    """

    name: str
    values: Dict[str, str] = field(default_factory=dict)
    errors: Dict[str, List[str]] = field(default_factory=dict)
    message: Optional[str] = None

    @property
    def valid(self) -> bool:
        """
        True if the submission had no errors
        """
        is_valid = len(self.errors) == 0
        return is_valid


class FormMail:
    """
    render a submission as a plain text mail and let the wiki send it
    """

    # fields of the submission that are not part of the message
    control_fields = {
        "wikicms_form",
        "captcha_answer",
        "captcha_expected",
        "postToken",
        "postToken_expected",
    }

    def __init__(
        self, form_def: FormDefinition, values: Dict[str, str], lang: str = "en"
    ):
        """
        Args:
            form_def(FormDefinition): the form definition
            values(dict): the submitted values keyed by field name
            lang(str): the language of the visit
        """
        self.form_def = form_def
        self.values = values
        self.lang = lang

    @property
    def subject(self) -> str:
        """
        the subject: the subject of the form definition, else its legend
        """
        subject = I18n.resolve(self.form_def.subject, self.lang)
        if not subject:
            subject = I18n.resolve(self.form_def.legend, self.lang)
        return subject

    @property
    def text(self) -> str:
        """
        the submission as label: value lines in the order of the form definition
        """
        lines = []
        for form_field in self.form_def.fields:
            if form_field.name in self.control_fields or form_field.field_type in (
                "hidden",
                "honeypot",
                "challenge",
            ):
                continue
            value = self.values.get(form_field.name, "")
            label = form_field.name
            if form_field.label is not None:
                label = I18n.resolve(form_field.label.text, self.lang) or label
            lines.append(f"{label}: {value}")
        text = "\n".join(lines)
        return text

    def send(self, site: Any) -> Dict[str, Any]:
        """
        send the mail to the recipient wiki user of the form definition

        Args:
            site: the mwclient Site of the frontend's logged in wiki client

        Returns:
            dict: the emailuser API result
        """
        token = site.api("query", meta="tokens")["query"]["tokens"]["csrftoken"]
        result = site.api(
            "emailuser",
            target=self.form_def.recipient,
            subject=self.subject,
            text=self.text,
            token=token,
        )
        return result
