"""
Created on 2026-03-30

@author: wf

Bootstrap 3 form renderer adapted from
https://github.com/LaunchPlatform/wtforms-bootstrap5/blob/master/wtforms_bootstrap5/renderers.py
Key difference: targets Bootstrap 3 class names instead of Bootstrap 5,
and resolves i18n strings via resolve_i18n().
"""

from typing import Dict, List, Optional

from markupsafe import Markup, escape

from frontend.forms.form_field import FormDefinition, FormField, resolve_i18n


class FormRenderer:
    """
    Renders a FormDefinition as Bootstrap 3 HTML using markupsafe.
    No Jinja2 - pure Python string/Markup building.

    All user-visible strings are resolved through resolve_i18n() so that
    multilingual form definitions (label/placeholder/error_msg as dicts) are
    rendered in the requested language.
    """

    def render(
        self,
        form_def: FormDefinition,
        values: Optional[Dict[str, str]] = None,
        errors: Optional[Dict[str, List[str]]] = None,
        lang: str = "en",
    ) -> str:
        """
        Render the form definition as Bootstrap 3 HTML.

        Args:
            form_def(FormDefinition): the form definition to render
            values(dict): optional pre-filled field values keyed by field name
            errors(dict): optional validation errors keyed by field name
            lang(str): language code for i18n resolution (default "en")

        Returns:
            str: rendered HTML string
        """
        if values is None:
            values = {}
        if errors is None:
            errors = {}

        legend = resolve_i18n(form_def.legend, lang)
        parts = []
        parts.append(
            Markup(
                f'<form class="form-horizontal" action="{escape(form_def.action)}" method="post">'
            )
        )
        parts.append(Markup(f"<fieldset><legend>{escape(legend)}</legend>"))

        for field in form_def.fields:
            parts.append(
                self._render_field(
                    field,
                    values.get(field.name, ""),
                    errors.get(field.name, []),
                    lang,
                )
            )

        parts.append(self._render_submit(form_def, lang))
        parts.append(Markup("</fieldset></form>"))

        return Markup("").join(parts)

    def _render_field(
        self, field: FormField, value: str, field_errors: List[str], lang: str = "en"
    ) -> Markup:
        """
        Render a single form field.

        Args:
            field(FormField): the field definition
            value(str): current field value
            field_errors(list): list of error messages for this field
            lang(str): language code for i18n resolution

        Returns:
            Markup: rendered field HTML
        """
        if field.field_type == "hidden":
            hidden_value = escape(value or field.value or "")
            return Markup(
                f'<input type="hidden" name="{escape(field.name)}" value="{hidden_value}">'
            )

        has_error = bool(field_errors)
        group_class = "form-group has-feedback" + (" has-error" if has_error else "")

        label_text = escape(resolve_i18n(field.label, lang) or field.name)

        parts = [Markup(f'<div class="{group_class}">')]
        parts.append(
            Markup(
                f'<label class="col-md-3 control-label bitplanorange" for="{escape(field.name)}">'
                f"{label_text}</label>"
            )
        )
        parts.append(
            Markup(
                '<div class="col-md-6 inputGroupContainer"><div class="input-group">'
            )
        )

        if field.glyphicon:
            parts.append(
                Markup(
                    f'<span class="input-group-addon">'
                    f'<i class="glyphicon glyphicon-{escape(field.glyphicon)}"></i>'
                    f"</span>"
                )
            )

        parts.append(self._render_input(field, value, lang))
        parts.append(Markup("</div>"))  # input-group

        for error in field_errors:
            parts.append(
                Markup(
                    f'<small class="help-block" data-bv-validator="notEmpty">'
                    f"{escape(error)}</small>"
                )
            )

        parts.append(Markup("</div></div>"))  # inputGroupContainer, form-group

        return Markup("").join(parts)

    def _render_input(self, field: FormField, value: str, lang: str = "en") -> Markup:
        """
        Render the input element for a field.

        Args:
            field(FormField): the field definition
            value(str): current field value
            lang(str): language code for i18n resolution

        Returns:
            Markup: rendered input HTML
        """
        placeholder = escape(resolve_i18n(field.placeholder, lang) or "")
        required_attr = ' required="required"' if field.required else ""
        field_name = escape(field.name)

        if field.field_type == "textarea":
            rendered = Markup(
                f'<textarea class="form-control" name="{field_name}" id="{field_name}" '
                f'placeholder="{placeholder}" data-bv-field="{field_name}"{required_attr}>'
                f"{escape(value)}</textarea>"
            )
        elif field.field_type == "select":
            choices = field.choices or []
            options = Markup("").join(
                Markup(
                    f'<option value="{escape(c)}"'
                    f"{'selected' if c == value else ''}>"
                    f"{escape(c)}</option>"
                )
                for c in choices
            )
            rendered = Markup(
                f'<select class="form-control" name="{field_name}" id="{field_name}" '
                f'data-bv-field="{field_name}"{required_attr}>{options}</select>'
            )
        else:
            # text and email field types both render as <input type="text">
            rendered = Markup(
                f'<input type="text" class="form-control" name="{field_name}" id="{field_name}" '
                f'placeholder="{placeholder}" value="{escape(value)}" '
                f'data-bv-field="{field_name}"{required_attr}>'
            )
        return rendered

    def _render_submit(self, form_def: FormDefinition, lang: str = "en") -> Markup:
        """
        Render the submit button row.

        Args:
            form_def(FormDefinition): the form definition
            lang(str): language code for i18n resolution

        Returns:
            Markup: rendered submit button HTML
        """
        submit_label = escape(form_def.resolved_submit_label(lang))
        icon = Markup("")
        if form_def.submit_glyphicon:
            icon = Markup(
                f'<i class="glyphicon glyphicon-{escape(form_def.submit_glyphicon)}"></i> '
            )
        return Markup(
            '<div class="form-group">'
            '<div class="col-md-offset-3 col-md-6">'
            f'<button type="submit" class="btn btn-primary">{icon}{submit_label}</button>'
            "</div></div>"
        )
