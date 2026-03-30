"""
Created on 2026-03-30

@author: wf
"""

import os

from basemkit.basetest import Basetest

from frontend.forms.form_field import FormDefinition, FormField
from frontend.forms.handler import FormHandler
from frontend.forms.registry import FormRegistry
from frontend.forms.renderer import FormRenderer
from frontend.htmlfilter import MediaWikiHtmlFilter

DEFAULT_FORMS_DIR = os.path.expanduser("~/.wikicms/forms")


def make_contact_form() -> FormDefinition:
    """
    Build the Kontaktformular demo form definition in Python.
    """
    return FormDefinition(
        name="contact",
        legend="Ihre Nachricht an uns",
        fields=[
            FormField(
                name="name",
                field_type="text",
                label="Name",
                placeholder="Ihr Name",
                glyphicon="user",
                required=True,
                error_msg="Bitte geben Sie Ihren Namen an.",
            ),
            FormField(
                name="email",
                field_type="text",
                label="E-Mail",
                placeholder="Ihre E-Mail-Adresse",
                glyphicon="envelope",
                required=True,
                error_msg="Bitte geben Sie Ihre E-Mail-Adresse an.",
            ),
            FormField(
                name="message",
                field_type="textarea",
                label="Nachricht",
                placeholder="Ihre Nachricht",
                glyphicon="pencil",
                required=True,
                error_msg="Bitte geben Sie eine Nachricht ein.",
            ),
            FormField(
                name="postToken",
                field_type="hidden",
                value="dummy-token",
            ),
        ],
        submit_label="Absenden",
        submit_glyphicon="send",
        success_message="Vielen Dank für Ihre Nachricht!",
    )


class TestForms(Basetest):
    """
    Tests for the frontend/forms subpackage.
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        # Reset singleton between tests
        FormRegistry._instance = None

    def test_form_definition_build(self):
        """
        Test building a FormDefinition in Python.
        """
        form_def = make_contact_form()
        self.assertEqual(form_def.name, "contact")
        self.assertEqual(form_def.legend, "Ihre Nachricht an uns")
        self.assertEqual(len(form_def.fields), 4)
        self.assertEqual(form_def.fields[0].name, "name")
        self.assertTrue(form_def.fields[0].required)

    def test_registry_register_and_get(self):
        """
        Test registering and retrieving a form from the registry.
        """
        form_def = make_contact_form()
        FormRegistry.register(form_def)
        retrieved = FormRegistry.get("contact")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "contact")
        self.assertIsNone(FormRegistry.get("nonexistent"))

    def test_renderer_renders_html(self):
        """
        Test that FormRenderer produces expected Bootstrap 3 HTML.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(form_def)
        if self.debug:
            print(html)
        self.assertIn("form-horizontal", html)
        self.assertIn("Ihre Nachricht an uns", html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn("<textarea", html)
        self.assertIn('type="hidden"', html)
        self.assertIn("glyphicon-user", html)
        self.assertIn("Absenden", html)
        self.assertIn("glyphicon-send", html)

    def test_renderer_with_values_and_errors(self):
        """
        Test that pre-filled values and errors are rendered.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(
            form_def,
            values={"name": "Max Mustermann", "email": "max@example.com"},
            errors={"email": ["Bitte geben Sie Ihre E-Mail-Adresse an."]},
        )
        if self.debug:
            print(html)
        self.assertIn("Max Mustermann", html)
        self.assertIn("has-error", html)
        self.assertIn("Bitte geben Sie Ihre E-Mail-Adresse an.", html)

    def test_handler_validate_missing_required(self):
        """
        Test that missing required fields produce errors.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def, {"name": "", "email": "", "message": ""}
        )
        self.assertIn("name", errors)
        self.assertIn("email", errors)
        self.assertIn("message", errors)

    def test_handler_validate_ok(self):
        """
        Test that a fully filled form produces no errors.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def,
            {"name": "Max", "email": "max@example.com", "message": "Hallo"},
        )
        self.assertEqual(errors, {})

    def test_htmlfilter_replaces_form_div(self):
        """
        Test that MediaWikiHtmlFilter replaces wikicms-form div with rendered form.
        """
        form_def = make_contact_form()
        FormRegistry.register(form_def)

        html = (
            '<div class="wikicms-form" data-form-name="contact">'
            '<a href="http://www.bitplan.com/Kontaktformular">Hier geht\'s zum Kontaktformular</a>'
            "</div>"
        )

        mwf = MediaWikiHtmlFilter(form_registry=FormRegistry.instance())
        result = mwf.filter_html(html)
        if self.debug:
            print(result)
        self.assertNotIn("wikicms-form", result)
        self.assertIn("form-horizontal", result)
        self.assertIn("Ihre Nachricht an uns", result)

    def test_load_forms_from_default_dir(self):
        """
        Test that all YAML files in ~/.wikicms/forms are loaded into the registry.
        """
        if not os.path.isdir(DEFAULT_FORMS_DIR):
            self.skipTest(f"{DEFAULT_FORMS_DIR} does not exist")
        for fname in sorted(os.listdir(DEFAULT_FORMS_DIR)):
            if fname.endswith(".yaml"):
                yaml_path = os.path.join(DEFAULT_FORMS_DIR, fname)
                FormRegistry.register_from_yaml(yaml_path)
        for expected_name in ("contact", "contacttest", "registration"):
            form_def = FormRegistry.get(expected_name)
            self.assertIsNotNone(
                form_def, f"form '{expected_name}' not found in registry"
            )
            if self.debug:
                renderer = FormRenderer()
                print(f"\n--- {expected_name} ---")
                print(renderer.render(form_def))

    def test_htmlfilter_no_registry_leaves_div(self):
        """
        Test that without a registry the wikicms-form div is left untouched.
        """
        html = (
            '<div class="wikicms-form" data-form-name="contact">'
            '<a href="http://www.bitplan.com/Kontaktformular">Hier geht\'s zum Kontaktformular</a>'
            "</div>"
        )
        mwf = MediaWikiHtmlFilter()
        result = mwf.filter_html(html)
        self.assertIn("wikicms-form", result)
