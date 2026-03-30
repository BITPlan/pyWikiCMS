"""
Created on 2026-03-30

@author: wf
"""

from basemkit.basetest import Basetest

from frontend.forms.form_field import FormDefinition, FormField
from frontend.forms.handler import FormHandler
from frontend.forms.registry import FormRegistry
from frontend.forms.renderer import FormRenderer
from frontend.htmlfilter import MediaWikiHtmlFilter


def make_contact_form() -> FormDefinition:
    """
    Build the Contact demo form definition in Python.
    """
    return FormDefinition(
        name="contact",
        legend="Send us a message",
        fields=[
            FormField(
                name="name",
                field_type="text",
                label="Name",
                placeholder="Your name",
                glyphicon="user",
                required=True,
                error_msg="Please enter your name.",
            ),
            FormField(
                name="email",
                field_type="text",
                label="E-Mail",
                placeholder="Your e-mail address",
                glyphicon="envelope",
                required=True,
                error_msg="Please enter your e-mail address.",
            ),
            FormField(
                name="message",
                field_type="textarea",
                label="Message",
                placeholder="Your message",
                glyphicon="pencil",
                required=True,
                error_msg="Please enter a message.",
            ),
            FormField(
                name="postToken",
                field_type="hidden",
                value="dummy-token",
            ),
        ],
        submit_label="Send",
        submit_glyphicon="send",
        success_message="Thank you for your message!",
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
        self.assertEqual(form_def.legend, "Send us a message")
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
        self.assertIn("Send us a message", html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn("<textarea", html)
        self.assertIn('type="hidden"', html)
        self.assertIn("glyphicon-user", html)
        self.assertIn("Send", html)
        self.assertIn("glyphicon-send", html)

    def test_renderer_with_values_and_errors(self):
        """
        Test that pre-filled values and errors are rendered.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(
            form_def,
            values={"name": "John Doe", "email": "john@example.com"},
            errors={"email": ["Please enter your e-mail address."]},
        )
        if self.debug:
            print(html)
        self.assertIn("John Doe", html)
        self.assertIn("has-error", html)
        self.assertIn("Please enter your e-mail address.", html)

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
            {"name": "John", "email": "john@example.com", "message": "Hello"},
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
            '<a href="http://www.bitplan.com/Contact">Contact form</a>'
            "</div>"
        )

        mwf = MediaWikiHtmlFilter(form_registry=FormRegistry.instance())
        result = mwf.filter_html(html)
        if self.debug:
            print(result)
        self.assertNotIn("wikicms-form", result)
        self.assertIn("form-horizontal", result)
        self.assertIn("Send us a message", result)

    def test_htmlfilter_no_registry_leaves_div(self):
        """
        Test that without a registry the wikicms-form div is left untouched.
        """
        html = (
            '<div class="wikicms-form" data-form-name="contact">'
            '<a href="http://www.bitplan.com/Contact">Contact form</a>'
            "</div>"
        )
        mwf = MediaWikiHtmlFilter()
        result = mwf.filter_html(html)
        self.assertIn("wikicms-form", result)
