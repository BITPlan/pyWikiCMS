"""
Created on 2026-03-30

@author: wf

Bootstrap 3 form renderer adapted from
https://github.com/LaunchPlatform/wtforms-bootstrap5/blob/master/wtforms_bootstrap5/renderers.py
Key difference: targets Bootstrap 3 class names instead of Bootstrap 5.
"""

from typing import Dict, List, Optional

from markupsafe import Markup

from frontend.forms.form_field import FormDefinition, FormField


class FormRenderer:
    """
    Renders a FormDefinition as Bootstrap 3 HTML using markupsafe.
    No Jinja2 - pure Python string/Markup building.
    """

    def render(
        self,
        form_def: FormDefinition,
        values: Optional[Dict[str, str]] = None,
        errors: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """
        Render the form definition as Bootstrap 3 HTML.

        Args:
            form_def(FormDefinition): the form definition to render
            values(dict): optional pre-filled field values keyed by field name
            errors(dict): optional validation errors keyed by field name

        Returns:
            str: rendered HTML string
        """
        if values is None:
            values = {}
        if errors is None:
            errors = {}

        parts = []
        parts.append(
            Markup(
                f'<form class="form-horizontal" action="{form_def.action}" method="post">'
            )
        )
        parts.append(Markup(f"<fieldset><legend>{form_def.legend}</legend>"))

        for field in form_def.fields:
            parts.append(
                self._render_field(
                    field, values.get(field.name, ""), errors.get(field.name, [])
                )
            )

        parts.append(self._render_submit(form_def))
        parts.append(Markup("</fieldset></form>"))

        return Markup("").join(parts)

    def _render_field(
        self, field: FormField, value: str, field_errors: List[str]
    ) -> Markup:
        """
        Render a single form field.

        Args:
            field(FormField): the field definition
            value(str): current field value
            field_errors(list): list of error messages for this field

        Returns:
            Markup: rendered field HTML
        """
        if field.field_type == "hidden":
            return Markup(
                f'<input type="hidden" name="{field.name}" value="{value or field.value or ""}">'
            )

        has_error = bool(field_errors)
        group_class = "form-group has-feedback" + (" has-error" if has_error else "")

        parts = [Markup(f'<div class="{group_class}">')]

        label_text = field.label or field.name
        parts.append(
            Markup(
                f'<label class="col-md-3 control-label bitplanorange" for="{field.name}">'
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
                    f'<span class="input-group-addon"><i class="glyphicon glyphicon-{field.glyphicon}"></i></span>'
                )
            )

        parts.append(self._render_input(field, value))

        parts.append(Markup("</div>"))  # input-group

        for error in field_errors:
            parts.append(
                Markup(
                    f'<small class="help-block" data-bv-validator="notEmpty">{error}</small>'
                )
            )

        parts.append(Markup("</div></div>"))  # inputGroupContainer, form-group

        return Markup("").join(parts)

    def _render_input(self, field: FormField, value: str) -> Markup:
        """
        Render the input element for a field.

        Args:
            field(FormField): the field definition
            value(str): current field value

        Returns:
            Markup: rendered input HTML
        """
        placeholder = field.placeholder or ""
        required_attr = ' required="required"' if field.required else ""

        if field.field_type == "textarea":
            return Markup(
                f'<textarea class="form-control" name="{field.name}" id="{field.name}" '
                f'placeholder="{placeholder}" data-bv-field="{field.name}"{required_attr}>'
                f"{value}</textarea>"
            )
        elif field.field_type == "select":
            choices = field.choices or []
            options = "".join(
                f'<option value="{c}"{"selected" if c == value else ""}>{c}</option>'
                for c in choices
            )
            return Markup(
                f'<select class="form-control" name="{field.name}" id="{field.name}" '
                f'data-bv-field="{field.name}"{required_attr}>{options}</select>'
            )
        else:
            return Markup(
                f'<input type="text" class="form-control" name="{field.name}" id="{field.name}" '
                f'placeholder="{placeholder}" value="{value}" '
                f'data-bv-field="{field.name}"{required_attr}>'
            )

    def _render_submit(self, form_def: FormDefinition) -> Markup:
        """
        Render the submit button row.

        Args:
            form_def(FormDefinition): the form definition

        Returns:
            Markup: rendered submit button HTML
        """
        icon = ""
        if form_def.submit_glyphicon:
            icon = Markup(
                f'<i class="glyphicon glyphicon-{form_def.submit_glyphicon}"></i> '
            )
        return Markup(
            '<div class="form-group">'
            '<div class="col-md-offset-3 col-md-6">'
            f'<button type="submit" class="btn btn-primary">{icon}{form_def.submit_label}</button>'
            "</div></div>"
        )
