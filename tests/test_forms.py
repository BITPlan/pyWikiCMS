"""
Created on 2026-03-30

@author: wf
"""

from pathlib import Path

from basemkit.basetest import Basetest

from frontend.forms.form_field import FormDefinition, FormField, resolve_i18n
from frontend.forms.handler import FormHandler
from frontend.forms.registry import FormRegistry
from frontend.forms.renderer import FormRenderer
from frontend.forms.validators import build_wtforms_validators, validate_with_wtforms
from frontend.htmlfilter import MediaWikiHtmlFilter, PageContent

# Path to the built-in contact.yaml shipped with the package
_CONTACT_YAML = (
    Path(__file__).parent.parent / "frontend" / "resources" / "forms" / "contact.yaml"
)


def make_contact_form() -> FormDefinition:
    """
    Build the Contact demo form definition in Python using i18n dicts and
    WTForms validator descriptors.
    """
    return FormDefinition(
        name="contact",
        legend={
            "en": "Contact us",
            "de": "Kontaktieren Sie uns",
            "fr": "Contactez-nous",
        },
        fields=[
            FormField(
                name="name",
                field_type="text",
                label={"en": "Name", "de": "Name", "fr": "Nom"},
                placeholder={"en": "Your name", "de": "Ihr Name", "fr": "Votre nom"},
                glyphicon="user",
                required=True,
                error_msg={
                    "en": "Please enter your name.",
                    "de": "Bitte geben Sie Ihren Namen ein.",
                    "fr": "Veuillez saisir votre nom.",
                },
                validators=[
                    {"type": "DataRequired"},
                    {"type": "Length", "min": 2, "max": 100},
                ],
            ),
            FormField(
                name="email",
                field_type="text",
                label={"en": "E-Mail", "de": "E-Mail"},
                placeholder={
                    "en": "Your e-mail address",
                    "de": "Ihre E-Mail-Adresse",
                },
                glyphicon="envelope",
                required=True,
                error_msg={
                    "en": "Please enter a valid e-mail address.",
                    "de": "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
                },
                validators=[
                    {"type": "DataRequired"},
                    {"type": "Email"},
                ],
            ),
            FormField(
                name="message",
                field_type="textarea",
                label={"en": "Message", "de": "Nachricht", "fr": "Message"},
                placeholder={"en": "Your message", "de": "Ihre Nachricht"},
                glyphicon="pencil",
                required=True,
                error_msg={
                    "en": "Please enter a message.",
                    "de": "Bitte geben Sie eine Nachricht ein.",
                },
                validators=[
                    {"type": "DataRequired"},
                    {"type": "Length", "min": 10, "max": 2000},
                ],
            ),
            FormField(
                name="postToken",
                field_type="hidden",
                value="dummy-token",
            ),
        ],
        submit_label={"en": "Send", "de": "Absenden", "fr": "Envoyer"},
        submit_glyphicon="send",
        success_message={
            "en": "Thank you for your message!",
            "de": "Vielen Dank für Ihre Nachricht!",
        },
    )


class TestForms(Basetest):
    """
    Tests for the frontend/forms subpackage.
    """

    def setUp(self, debug=True, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)
        # Reset singleton between tests
        FormRegistry._instance = None

    def test_resolve_i18n(self):
        """
        Test resolve_i18n with dict, plain string, and None values.
        """
        msg = {"en": "Hello", "de": "Hallo", "fr": "Bonjour"}
        self.assertEqual(resolve_i18n(msg, "en"), "Hello")
        self.assertEqual(resolve_i18n(msg, "de"), "Hallo")
        self.assertEqual(resolve_i18n(msg, "fr"), "Bonjour")
        # unknown lang falls back to "en"
        self.assertEqual(resolve_i18n(msg, "xx"), "Hello")
        # plain string passes through unchanged
        self.assertEqual(resolve_i18n("plain", "de"), "plain")
        # None returns empty string
        self.assertEqual(resolve_i18n(None, "en"), "")

    def test_form_definition_build(self):
        """
        Test building a FormDefinition in Python with i18n dicts.
        """
        form_def = make_contact_form()
        self.assertEqual(form_def.name, "contact")
        self.assertIsInstance(form_def.legend, dict)
        self.assertEqual(resolve_i18n(form_def.legend, "en"), "Contact us")
        self.assertEqual(resolve_i18n(form_def.legend, "de"), "Kontaktieren Sie uns")
        self.assertEqual(len(form_def.fields), 4)
        self.assertEqual(form_def.fields[0].name, "name")
        self.assertTrue(form_def.fields[0].required)

    def test_resolved_submit_label(self):
        """
        Test resolved_submit_label for multiple languages and fallback.
        """
        form_def = make_contact_form()
        self.assertEqual(form_def.resolved_submit_label("en"), "Send")
        self.assertEqual(form_def.resolved_submit_label("de"), "Absenden")
        self.assertEqual(form_def.resolved_submit_label("fr"), "Envoyer")
        # unknown lang: falls back to built-in English default
        self.assertEqual(form_def.resolved_submit_label("xx"), "Send")

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

    def test_registry_loads_builtin_contact(self):
        """
        Test that the registry auto-loads the built-in contact.yaml.
        """
        # Reset so of_forms_dir() runs fresh
        FormRegistry._instance = None
        registry = FormRegistry.of_forms_dir("/nonexistent/path")
        contact = registry._forms.get("contact")
        self.assertIsNotNone(contact, "Built-in contact form not loaded")
        self.assertEqual(contact.name, "contact")
        # legend should be a multilingual dict
        self.assertIsInstance(contact.legend, dict)
        self.assertIn("en", contact.legend)
        self.assertIn("de", contact.legend)

    def test_contact_yaml_load(self):
        """
        Test that contact.yaml loads correctly as a FormDefinition.
        """
        self.assertTrue(
            _CONTACT_YAML.exists(), f"contact.yaml not found: {_CONTACT_YAML}"
        )
        form_def = FormDefinition.load_from_yaml_file(str(_CONTACT_YAML))  # @UndefinedVariable
        self.assertEqual(form_def.name, "contact")
        self.assertEqual(resolve_i18n(form_def.legend, "en"), "Contact us")
        self.assertEqual(resolve_i18n(form_def.legend, "de"), "Kontaktieren Sie uns")
        # validators declared on fields
        name_field = next(f for f in form_def.fields if f.name == "name")
        self.assertIsNotNone(name_field.validators)
        validator_types = [v["type"] for v in name_field.validators]
        self.assertIn("DataRequired", validator_types)
        self.assertIn("Length", validator_types)
        email_field = next(f for f in form_def.fields if f.name == "email")
        email_types = [v["type"] for v in email_field.validators]
        self.assertIn("Email", email_types)

    def test_build_wtforms_validators(self):
        """
        Test that build_wtforms_validators produces live WTForms validator instances.
        """
        import wtforms.validators as wv

        form_def = make_contact_form()
        name_field = form_def.fields[0]
        validators = build_wtforms_validators(name_field, lang="en")
        self.assertTrue(len(validators) >= 1)
        # first validator should be DataRequired
        self.assertIsInstance(validators[0], wv.DataRequired)
        # second should be Length
        self.assertIsInstance(validators[1], wv.Length)
        self.assertEqual(validators[1].min, 2)
        self.assertEqual(validators[1].max, 100)

    def test_renderer_renders_html_english(self):
        """
        Test that FormRenderer produces expected Bootstrap 3 HTML in English.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(form_def, lang="en")
        if self.debug:
            print(html)
        self.assertIn("form-horizontal", html)
        self.assertIn("Contact us", html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn("<textarea", html)
        self.assertIn('type="hidden"', html)
        self.assertIn("glyphicon-user", html)
        self.assertIn("Send", html)
        self.assertIn("glyphicon-send", html)

    def test_renderer_renders_html_german(self):
        """
        Test that FormRenderer resolves German i18n strings.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(form_def, lang="de")
        if self.debug:
            print(html)
        self.assertIn("Kontaktieren Sie uns", html)
        self.assertIn("Ihr Name", html)
        self.assertIn("Absenden", html)
        self.assertNotIn("Contact us", html)

    def test_renderer_with_values_and_errors(self):
        """
        Test that pre-filled values and errors are rendered correctly.
        """
        form_def = make_contact_form()
        renderer = FormRenderer()
        html = renderer.render(
            form_def,
            values={"name": "John Doe", "email": "john@example.com"},
            errors={"email": ["Please enter a valid e-mail address."]},
            lang="en",
        )
        if self.debug:
            print(html)
        self.assertIn("John Doe", html)
        self.assertIn("has-error", html)
        self.assertIn("Please enter a valid e-mail address.", html)

    def test_handler_validate_missing_required(self):
        """
        Test that missing required fields produce WTForms errors.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def, {"name": "", "email": "", "message": ""}, lang="en"
        )
        if self.debug:
            print("errors:", errors)
        self.assertIn("name", errors)
        self.assertIn("email", errors)
        self.assertIn("message", errors)

    def test_handler_validate_short_name(self):
        """
        Test that a too-short name triggers a Length validator error.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def,
            {
                "name": "X",
                "email": "ok@example.com",
                "message": "Hello world this is fine",
            },
            lang="en",
        )
        self.assertIn("name", errors)

    def test_handler_validate_invalid_email(self):
        """
        Test that an invalid email triggers an Email validator error.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def,
            {
                "name": "John",
                "email": "not-an-email",
                "message": "Hello world this is fine",
            },
            lang="en",
        )
        self.assertIn("email", errors)

    def test_handler_validate_ok(self):
        """
        Test that a fully valid form produces no errors.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def,
            {
                "name": "John Doe",
                "email": "john@example.com",
                "message": "Hello, this is a valid message.",
            },
            lang="en",
        )
        self.assertEqual(errors, {})

    def test_handler_validate_german_errors(self):
        """
        Test that German error messages are returned when lang='de'.
        """
        form_def = make_contact_form()
        errors = FormHandler.validate(
            form_def,
            {"name": "", "email": "", "message": ""},
            lang="de",
        )
        self.assertIn("name", errors)
        name_errors = errors["name"]
        self.assertTrue(
            any("Bitte" in e or "geben" in e for e in name_errors),
            f"Expected German error, got: {name_errors}",
        )

    def test_handler_captcha_error_i18n(self):
        """
        Test that captcha error messages are localised.
        """
        form_def = make_contact_form()
        post_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Hello, this is a valid message.",
            "captcha_answer": "wrong",
            "captcha_expected": "correct",
        }
        errors_en = FormHandler.validate(form_def, post_data, lang="en")
        errors_de = FormHandler.validate(form_def, post_data, lang="de")
        self.assertIn("captcha_answer", errors_en)
        self.assertIn("captcha_answer", errors_de)
        self.assertNotEqual(errors_en["captcha_answer"], errors_de["captcha_answer"])
        self.assertIn("incorrect", errors_en["captcha_answer"][0])
        self.assertIn("korrekt", errors_de["captcha_answer"][0])

    def test_handler_token_error_i18n(self):
        """
        Test that postToken error messages are localised.
        """
        form_def = make_contact_form()
        post_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Hello, this is a valid message.",
            "postToken": "bad-token",
            "postToken_expected": "good-token",
        }
        errors_en = FormHandler.validate(form_def, post_data, lang="en")
        errors_de = FormHandler.validate(form_def, post_data, lang="de")
        self.assertIn("postToken", errors_en)
        self.assertIn("postToken", errors_de)
        self.assertIn("Invalid", errors_en["postToken"][0])
        self.assertIn("Ungültig", errors_de["postToken"][0])

    def test_htmlfilter_replaces_form_div(self):
        """
        Test that MediaWikiHtmlFilter replaces wikicms-form div with rendered form.
        """
        form_def = make_contact_form()
        FormRegistry.register(form_def)
        pc=PageContent()
        pc.html = (
            '<div class="wikicms-form" data-form-name="contact">'
            '<a href="http://www.bitplan.com/Contact">Contact form</a>'
            "</div>"
        )
        mwf = MediaWikiHtmlFilter()
        result = mwf.filter_html(pc)
        if self.debug:
            print(result)
        self.assertNotIn("wikicms-form", result)
        self.assertIn("form-horizontal", result)
        self.assertIn("Contact us", result)

    def test_htmlfilter_no_registry_leaves_div(self):
        """
        Test that without a registry the wikicms-form div is left untouched.
        """
        # Ensure no registry is active
        FormRegistry._instance = None
        # Prevent auto-loading built-ins by injecting a blank registry
        blank = FormRegistry()
        FormRegistry._instance = blank

        html = (
            '<div class="wikicms-form" data-form-name="contact">'
            '<a href="http://www.bitplan.com/Contact">Contact form</a>'
            "</div>"
        )
        mwf = MediaWikiHtmlFilter()
        result = mwf.filter_html(html)
        self.assertIn("wikicms-form", result)
