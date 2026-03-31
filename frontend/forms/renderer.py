"""
Created on 2026-03-30

@author: wf

Bootstrap 3 form renderer.
Produces HTML matching the original Rythm template output from
MediaWiki:Form.rythm (preField/postField/showFormContent).
"""

from typing import Dict, List, Optional

from markupsafe import Markup, escape

from frontend.forms.form_field import FormDefinition, FormField, I18n


class FormRenderer:
    """
    Renders a FormDefinition as Bootstrap 3 HTML using markupsafe.

    All user-visible strings are resolved through I18n.resolve() so that
    multilingual form definitions (label/placeholder/error_msg as dicts)
    are rendered in the requested language.

    Indentation matches the original Rythm template output.
    """

    # Indentation constants matching the original Rythm template
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
        form_css_class = (
            form_def.css_class
            if hasattr(form_def, "css_class") and form_def.css_class
            else "form-horizontal"
        )

        parts = []
        parts.append(
            Markup(
                f'{self.I2}<form class="{form_css_class}" action="{escape(form_def.action)}" method="post">\n'
            )
        )
        parts.append(
            Markup(
                f"{self.I4}<fieldset>\n"
                f"{self.I4}<!-- Form Name -->\n"
                f"{self.I4}<legend>{escape(legend)}</legend>\n"
            )
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
            rendered = Markup(
                f'{self.I8}<input type="hidden" name="{escape(field.name)}"'
                f' id="{escape(field.name)}" value="{hidden_value}">\n'
            )
            return rendered

        # Resolve label — always a FormLabel object
        label = field.label
        label_text = escape(I18n.resolve(label.text, lang) if label else "") or escape(
            field.name
        )
        label_extra_css = label.css_class if label and label.css_class else ""

        # Build label css class
        size_css = "col-md-3 control-label"
        label_css = (
            f"{label_extra_css} {size_css}".strip() if label_extra_css else size_css
        )

        parts = []
        # form-group open
        parts.append(Markup(f'{self.I8}<div class="form-group">\n'))
        # label
        parts.append(
            Markup(f'{self.I10}<label class="{label_css}">{label_text}</label>  \n')
        )
        # input container open
        parts.append(
            Markup(
                f'{self.I10}<div class="col-md-6 inputGroupContainer">\n'
                f'{self.I12}<div class="input-group">\n'
            )
        )
        # glyphicon addon
        if field.glyphicon:
            parts.append(
                Markup(
                    f'{self.I14}<span class="input-group-addon">'
                    f'<i class="glyphicon glyphicon-{escape(field.glyphicon)}"></i>'
                    f"</span>\n"
                )
            )
        # input element
        parts.append(
            Markup(f"{self.I14}")
            + self._render_input(field, value, lang)
            + Markup("\n")
        )
        # input container close
        parts.append(Markup(f"{self.I12}</div>\n{self.I10}</div>\n"))
        # error messages
        for error in field_errors:
            parts.append(
                Markup(
                    f'{self.I10}<small class="help-block" data-bv-validator="notEmpty">'
                    f"{escape(error)}</small>\n"
                )
            )
        # form-group close
        parts.append(Markup(f"{self.I8}</div>\n"))

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
        base_class = field.css_class if field.css_class else "form-control"

        if field.field_type == "textarea":
            rendered = Markup(
                f'<textarea name="{field_name}" id="{field_name}"'
                f' placeholder="{placeholder}" class="{base_class}">'
                f"{escape(value)}</textarea>"
            )
        elif field.field_type == "select":
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
            if "selectpicker" not in base_class:
                base_class = f"{base_class} selectpicker"
            rendered = Markup(
                f'<select name="{field_name}" id="{field_name}"'
                f' class="{base_class}">\n'
                f"{options}\n"
                f"{self.I14}</select>"
            )
        else:
            rendered = Markup(
                f'<input type="text" name="{field_name}" id="{field_name}"'
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
        icon = Markup("")
        if form_def.submit_glyphicon:
            icon = Markup(
                f'<span class="glyphicon glyphicon-{escape(form_def.submit_glyphicon)}"></span>'
            )
        result = Markup(
            f"{self.I8}<!-- Button -->\n"
            f'{self.I8}<div class="form-group">\n'
            f'{self.I10}<label class="col-md-4 control-label"></label>\n'
            f'{self.I10}<div class="col-md-4">\n'
            f'{self.I12}<button type="submit">{submit_label}{icon}</button>\n'
            f"{self.I10}</div>\n"
            f"{self.I8}</div>\n"
        )
        return result
