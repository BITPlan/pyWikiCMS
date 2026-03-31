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

from frontend.forms.form_field import FormDefinition, FormField, I18n


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

        legend = I18n.resolve(form_def.legend, lang)
        # Use css_class from form definition, default to "form-horizontal"
        form_css_class = (
            form_def.css_class
            if hasattr(form_def, "css_class") and form_def.css_class
            else "form-horizontal"
        )
        parts = []
        parts.append(
            Markup(
                f'<form class="{form_css_class}" action="{escape(form_def.action)}" method="post">\n'
            )
        )
        parts.append(Markup(f"<fieldset>\n<legend>{escape(legend)}</legend>\n"))

        for field in form_def.fields:
            field_html=self._render_field(
                    field,
                    values.get(field.name, ""),
                    errors.get(field.name, []),
                    lang,
                )
            parts.append(field_html)

        parts.append(self._render_submit(form_def, lang))
        parts.append(Markup("</fieldset>\n</form>"))

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

        # Handle label - can be string/dict (backward compat) or FormLabel object
        if hasattr(field.label, "text"):
            # New FormLabel format
            label_text = escape(I18n.resolve(field.label.text, lang) or field.name)
            label_extra_css = field.label.css_class if field.label.css_class else ""
        else:
            # Old format: string or dict
            label_text = escape(I18n.resolve(field.label, lang) or field.name)
            label_extra_css = ""

        # Build label css_class - use label_extra_css + size-based classes
        label_size = field.size if field.size else "md"
        size_css = f"col-{label_size}-3 control-label"
        label_css = f"{label_extra_css} {size_css}".strip()

        parts = [Markup(f'<div class="{group_class}">\n')]
        parts.append(
            Markup(
                f'  <label class="{label_css}" for="{escape(field.name)}">'
                f"{label_text}</label>\n"
            )
        )

        # Use size for input container
        input_size = field.size if field.size else "md"
        parts.append(
            Markup(
                f'  <div class="col-{input_size}-6 inputGroupContainer">\n'
                f'    <div class="input-group">\n'
            )
        )

        if field.glyphicon:
            parts.append(
                Markup(
                    f'      <span class="input-group-addon">'
                    f'<i class="glyphicon glyphicon-{escape(field.glyphicon)}"></i>'
                    f"</span>\n"
                )
            )

        parts.append(
            Markup("      ") + self._render_input(field, value, lang) + Markup("\n")
        )

        parts.append(Markup("    </div>\n"))  # input-group

        for error in field_errors:
            parts.append(
                Markup(
                    f'    <small class="help-block" data-bv-validator="notEmpty">'
                    f"{escape(error)}</small>\n"
                )
            )

        parts.append(Markup("  </div>\n</div>\n"))  # inputGroupContainer, form-group

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
        placeholder = escape(I18n.resolve(field.placeholder, lang) or "")
        required_attr = ' required="required"' if field.required else ""
        field_name = escape(field.name)

        # Build css_class - use field.css_class or default to "form-control"
        base_class = field.css_class if field.css_class else "form-control"

        if field.field_type == "textarea":
            rendered = Markup(
                f'<textarea class="{base_class}" name="{field_name}" id="{field_name}" '
                f'placeholder="{placeholder}" data-bv-field="{field_name}"{required_attr}>\n'
                f"{escape(value)}</textarea>"
            )
        elif field.field_type == "select":
            choices = field.choices or []
            # Add placeholder choice if specified
            placeholder_choice = I18n.resolve(field.placeholder_choice, lang)
            options_parts = []
            if placeholder_choice:
                selected_attr = " selected" if not value else ""
                options_parts.append(
                    Markup(
                        f'<option value=" "{selected_attr}>{escape(placeholder_choice)}</option>'
                    )
                )
            for c in choices:
                selected_attr = " selected" if c == value else ""
                options_parts.append(
                    Markup(
                        f'<option value="{escape(c)}"{selected_attr}>{escape(c)}</option>'
                    )
                )
            options = Markup("\n").join(options_parts)
            # Add selectpicker class if not already in css_class
            if "selectpicker" not in base_class:
                base_class = f"{base_class} selectpicker"
            rendered = Markup(
                f'<select class="{base_class}" name="{field_name}" id="{field_name}" '
                f'data-bv-field="{field_name}"{required_attr}>\n'
                f"{options}\n</select>"
            )
        else:
            # text and email field types both render as <input type="text">
            rendered = Markup(
                f'<input type="text" class="{base_class}" name="{field_name}" id="{field_name}" '
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
            '  <div class="form-group">\n'
            '    <div class="col-md-offset-3 col-md-6">\n'
            f'      <button type="submit" class="btn btn-primary">{icon}{submit_label}</button>\n'
            "    </div>\n  </div>\n"
        )
