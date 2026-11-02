"""
Created on 2026-03-30

@author: wf

Form renderer with Bootstrap 5 class names, see issue 37.
"""

from typing import Dict, List, Optional

from markupsafe import Markup, escape

from frontend.forms.form_field import FormDefinition, FormField, I18n


class FormRenderer:
    """
    Renders a FormDefinition as semantic HTML with Bootstrap 5 class names
    using markupsafe.

    The markup carries no script and no client side validator; validation
    is done server side by FormHandler. A site without Bootstrap gets a
    plain usable form, a site with Bootstrap 5 on MediaWiki:Common.css or a
    Chameleon 6 wiki gets the styled one.

    All user-visible strings are resolved through I18n.resolve() so that
    multilingual form definitions (label/placeholder/error_msg as dicts)
    are rendered in the requested language.
    """

    # Indentation constants
    I2 = "  "
    I4 = "    "
    I8 = "        "
    I10 = "          "
    I12 = "            "
    I14 = "              "

    def render(
        self,
        form_def: FormDefinition,
        values: Optional[Dict[str, str]] = None,
        errors: Optional[Dict[str, List[str]]] = None,
        lang: str = "en",
    ) -> str:
        """
        Render the form definition as HTML.

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
        form_css_class = (
            form_def.css_class
            if hasattr(form_def, "css_class") and form_def.css_class
            else "wikicms-form"
        )

        parts = []
        parts.append(
            Markup(
                f'{self.I2}<form class="{form_css_class}" action="{escape(form_def.action)}" method="post">\n'
            )
        )
        parts.append(
            Markup(f"{self.I4}<fieldset>\n{self.I4}<legend>{escape(legend)}</legend>\n")
        )

        for field in form_def.fields:
            field_html = self._render_field(
                field,
                values.get(field.name, ""),
                errors.get(field.name, []),
                lang,
            )
            parts.append(field_html)

        parts.append(self._render_submit(form_def, lang))
        parts.append(Markup(f"{self.I4}</fieldset>\n{self.I2}</form>\n"))

        result = Markup("").join(parts)
        return result

    def _render_field(
        self, field: FormField, value: str, field_errors: List[str], lang: str = "en"
    ) -> Markup:
        """
        Render a single form field as a Bootstrap 5 row.

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
            rendered = Markup(
                f'{self.I8}<input type="hidden" name="{escape(field.name)}"'
                f' id="{escape(field.name)}" value="{hidden_value}">\n'
            )
            return rendered

        label = field.label
        label_text = escape(I18n.resolve(label.text, lang) if label else "") or escape(
            field.name
        )
        label_extra_css = label.css_class if label and label.css_class else ""
        size_css = "col-md-3 col-form-label"
        label_css = (
            f"{label_extra_css} {size_css}".strip() if label_extra_css else size_css
        )
        field_name = escape(field.name)

        parts = []
        parts.append(Markup(f'{self.I8}<div class="mb-3 row">\n'))
        parts.append(
            Markup(
                f'{self.I10}<label class="{label_css}" for="{field_name}">{label_text}</label>\n'
            )
        )
        parts.append(Markup(f'{self.I10}<div class="col-md-6">\n'))
        parts.append(
            Markup(f"{self.I12}")
            + self._render_input(field, value, lang)
            + Markup("\n")
        )
        for error in field_errors:
            parts.append(
                Markup(
                    f'{self.I12}<div class="invalid-feedback d-block">'
                    f"{escape(error)}</div>\n"
                )
            )
        parts.append(Markup(f"{self.I10}</div>\n{self.I8}</div>\n"))

        result = Markup("").join(parts)
        return result

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
        field_name = escape(field.name)

        if field.field_type == "textarea":
            base_class = field.css_class if field.css_class else "form-control"
            rendered = Markup(
                f'<textarea name="{field_name}" id="{field_name}"'
                f' placeholder="{placeholder}" class="{base_class}">'
                f"{escape(value)}</textarea>"
            )
        elif field.field_type == "select":
            base_class = field.css_class if field.css_class else "form-select"
            choices = field.choices or []
            placeholder_choice = I18n.resolve(field.placeholder_choice, lang)
            options_parts = []
            if placeholder_choice:
                selected_attr = " selected" if not value else ""
                options_parts.append(
                    Markup(
                        f'{self.I14}<option value=" "{selected_attr}>'
                        f"{escape(placeholder_choice)}</option>"
                    )
                )
            for c in choices:
                selected_attr = " selected" if c == value else ""
                options_parts.append(
                    Markup(f"{self.I14}<option{selected_attr}>{escape(c)}</option>")
                )
            options = Markup("\n").join(options_parts)
            rendered = Markup(
                f'<select name="{field_name}" id="{field_name}"'
                f' class="{base_class}">\n'
                f"{options}\n"
                f"{self.I12}</select>"
            )
        else:
            base_class = field.css_class if field.css_class else "form-control"
            input_type = "email" if field.field_type == "email" else "text"
            rendered = Markup(
                f'<input type="{input_type}" name="{field_name}" id="{field_name}"'
                f' placeholder="{placeholder}" class="{base_class}"'
                f' value="{escape(value)}">'
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
        result = Markup(
            f'{self.I8}<div class="mb-3 row">\n'
            f'{self.I10}<div class="col-md-6 offset-md-3">\n'
            f'{self.I12}<button type="submit" class="btn btn-primary">{submit_label}</button>\n'
            f"{self.I10}</div>\n"
            f"{self.I8}</div>\n"
        )
        return result
