# Implementation Plan: Python-based declarative form handling

Fixes issue https://github.com/BITPlan/pyWikiCMS/issues/33

## Overview

Replace `MediaWiki:Form.rythm` (Java/Rythm template) with a
`frontend/forms/` subpackage that renders Bootstrap 3 forms
from YAML-declared `lod_storable` dataclasses, using `wtforms`
https://github.com/pallets-eco/wtforms/ for field validation.

The renderer is adapted from
https://github.com/LaunchPlatform/wtforms-bootstrap5/tree/master/wtforms_bootstrap5
targeting Bootstrap 3 class names instead of Bootstrap 5.

---

## i18n (Internationalization)

All user-visible strings (legends, labels, placeholders, error messages, submit
labels) support multilingual values.  A translatable field may be either a
plain string or a language-keyed dict:

```yaml
legend:
  en: Contact us
  de: Kontaktieren Sie uns
  fr: Contactez-nous
```

`resolve_i18n(value, lang)` in `form_field.py` resolves the dict to a string at
render/validate time.  Unknown languages fall back to `"en"`, then to the first
available value.

---

## Trigger mechanism

The existing wiki page for Kontaktformular currently uses `{{UseFrame|...}}`:

```mediawiki
{{Language|master page=Contactform|language=de}}
{{UseFrame|Contact.rythm|title=Hier geht's zum Kontaktformular}}
[[Category:frontend]]
```

This is **replaced** by the new `{{UseForm|<formname>|title=}}` template. Example:

```mediawiki
{{Language|master page=Contactform|language=de}}
{{UseForm|contact|title=Hier geht's zum Kontaktformular}}
[[Category:frontend]]
```

The `{{UseForm|<formname>}}` template expands to a detectable HTML marker:

```html
<div class="wikicms-form" data-form-name="contact">
...
</div>
```

- **In the wiki** (viewed directly): shows a clickable link to the frontend page
- **In the frontend**: `MediaWikiHtmlFilter.filter_html()` detects
  `<div class="wikicms-form" data-form-name="...">`, looks up `data-form-name`
  in `FormRegistry`, renders the form via `FormRenderer`, replaces the entire
  `<div>` with the rendered form HTML

---

## Startup registration

Built-in example forms are shipped in `frontend/resources/forms/*.yaml` and
loaded automatically by `FormRegistry`.  User-defined forms are loaded from
`~/.wikicms/forms/*.yaml` and may override built-ins by name.

---

## File structure

```
frontend/forms/
    __init__.py        # exports: FormDefinition, FormField, FormHandler,
                       #          FormRegistry, FormRenderer,
                       #          build_wtforms_validators, resolve_i18n,
                       #          validate_with_wtforms
    form_field.py      # lod_storable dataclasses: FormField, FormDefinition
                       # + resolve_i18n() helper
    registry.py        # FormRegistry singleton: register / register_from_yaml / get
                       # auto-loads frontend/resources/forms/ then ~/.wikicms/forms/
    renderer.py        # Bootstrap 3 HTML renderer, lang= param, resolve_i18n()
    handler.py         # POST validation + captcha + postToken (i18n error messages)
    validators.py      # build_wtforms_validators(), validate_with_wtforms()

frontend/resources/forms/
    contact.yaml       # Built-in multilingual contact form example

tests/
    test_forms.py      # 19 tests: i18n, wtforms validators, yaml load,
                       #           render EN/DE, validate, htmlfilter
```

---

## `form_field.py` - lod_storable dataclasses

```python
I18nStr = Optional[Union[str, Dict[str, str]]]

def resolve_i18n(value: I18nStr, lang: str = "en") -> str:
    """Resolve a plain string or {lang: str} dict to a string."""
    ...

@lod_storable
class FormField:
    name: str
    field_type: str          # text | textarea | select | hidden
    label: Any = None        # I18nStr
    placeholder: Any = None  # I18nStr
    glyphicon: Optional[str] = None
    required: bool = False
    error_msg: Any = None    # I18nStr
    value: Optional[str] = None       # for hidden fields
    choices: Optional[List[str]] = None  # for select fields
    validators: Optional[List[Dict[str, Any]]] = None  # WTForms descriptors

@lod_storable
class FormDefinition:
    name: str
    legend: Any              # I18nStr - required
    fields: List[FormField]
    action: str = ""
    submit_label: Any = None  # I18nStr; resolved via resolved_submit_label(lang)
    submit_glyphicon: Optional[str] = None
    success_message: Any = None  # I18nStr
```

---

## `validators.py` - WTForms integration

```python
def build_wtforms_validators(field: FormField, lang: str = "en") -> List[Any]:
    """Build live WTForms validator instances from field.validators descriptors."""
    ...

def validate_with_wtforms(
    form_def: FormDefinition, post_data: Dict[str, str], lang: str = "en"
) -> Dict[str, List[str]]:
    """Run WTForms validators for all non-hidden fields. Returns error dict."""
    ...
```

Supported validator `type` values: `DataRequired`, `InputRequired`, `Optional`,
`Email`, `Length` (min/max), `NumberRange` (min/max), `Regexp`, `URL`,
`IPAddress`, `MacAddress`, `UUID`, `AnyOf`, `NoneOf`.

`StopValidation` (raised by `DataRequired`) halts the validator chain for the
field and is collected as an error.  `ValidationError` continues the chain.

---

## `renderer.py` - Bootstrap 3 renderer

`FormRenderer.render(form_def, values=None, errors=None, lang="en") -> str`

Each visible field renders the Bootstrap 3 pattern:
```
div.form-group.has-feedback[.has-error]
  label.col-md-3.control-label.bitplanorange
  div.col-md-6.inputGroupContainer
    div.input-group
      span.input-group-addon > i.glyphicon.<glyphicon>
      input|textarea|select.form-control[data-bv-field]
    small.help-block per error
```

Hidden fields emit bare `<input type="hidden">`.  All user content is escaped
via `markupsafe.escape()`.  No Jinja2.

---

## `handler.py` - POST validation

`FormHandler.validate(form_def, post_data, lang="en") -> dict[str, list[str]]`

- Delegates field validation to `validate_with_wtforms()`
- Validates captcha via `captcha_answer` / `captcha_expected` hidden fields
- Validates `postToken` / `postToken_expected` hidden fields
- All error messages are fully i18n: EN, DE, FR, ES, IT, NL built in

---

## `htmlfilter.py` changes

`MediaWikiHtmlFilter` gains an optional `form_registry: Optional[FormRegistry]`
constructor parameter.  `filter_html()` detects
`<div class="wikicms-form" data-form-name="...">` and replaces it with rendered
form HTML when `form_registry` is set.

`FormRegistry` is a singleton; the `form_registry` parameter passed to
`MediaWikiHtmlFilter` is the `FormRegistry` class itself (not an instance).

---

## `webserver.py` changes

`CmsWebServer` accepts an optional `form_registry: Optional[FormRegistry]` that
the deployer passes in at startup and forwards to `MediaWikiHtmlFilter`.

---

## POST route

The deployer wires their own FastAPI POST route and calls
`FormHandler.validate(form_def, post_data, lang=lang)`.  The library does not
auto-register routes.
