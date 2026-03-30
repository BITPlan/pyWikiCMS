# Implementation Plan: Python-based declarative form handling

Fixes issue https://github.com/BITPlan/pyWikiCMS/issues/33

## Overview

Replace `MediaWiki:Form.rythm` (Java/Rythm template) with a
`frontend/forms/` subpackage that renders Bootstrap 3 forms
from YAML-declared `lod_storable` dataclasses, using `wtforms` for field validation.

Code from https://github.com/LaunchPlatform/wtforms-bootstrap5/tree/master/wtforms_bootstrap5 is reused specifically:
- `renderers.py` - the per-field renderer logic (adapted from Bootstrap 5 to Bootstrap 3)
- `layout.py` - the `Column`, `Row`, `Fieldset` layout primitives

---

## Trigger mechanism

The existing wiki page for Kontaktformular currently uses `{{UseFrame|...}}`:

```mediawiki
{{Language|master page=Contactform|language=de}}
{{UseFrame|Contact.rythm|title=Hier geht's zum Kontaktformular}}
[[Category:frontend]]
```

This is **replaced** by the new `{{UseForm|<formname>}}` template. Example:

```mediawiki
{{Language|master page=Contactform|language=de}}
{{UseForm|contact}}
[[Category:frontend]]
```

The `{{UseForm|<formname>}}` template expands to a detectable HTML marker:

```html
<div class="wikicms-form" data-form-name="contact">
  <a href="http://www.bitplan.com/{{FULLPAGENAME}}">Hier geht's zum Kontaktformular</a>
</div>
```

- **In the wiki** (viewed directly): shows a clickable link to the frontend page, matching the `UseFrame` behaviour of `[http://www.bitplan.com/{{FULLPAGENAME}} {{{title|}}}]`
- **In the frontend**: `MediaWikiHtmlFilter.filter_html()` detects `<div class="wikicms-form" data-form-name="...">`, looks up `data-form-name` in `FormRegistry`, renders the form via `FormRenderer`, replaces the entire `<div>` with the rendered form HTML

---

## Startup registration

Forms are **not shipped** with the library except for a simple demo form.
The forms to be used in an application are registered at
application startup via a CLI parameter specifying YAML files with form declarations.

```python
from frontend.forms import FormRegistry
FormRegistry.register_from_yaml(form_yaml_path)
```

---

## File structure

```
frontend/forms/
    __init__.py        # exports FormDefinition, FormField, FormRegistry, FormRenderer, FormHandler
    form_field.py      # lod_storable dataclasses: FormField, FormDefinition
    registry.py        # FormRegistry singleton: register / register_from_yaml / get
    renderer.py        # Bootstrap 3 HTML renderer adapted from wtforms-bootstrap5 renderers.py
    handler.py         # POST validation + captcha + postToken

tests/
    test_forms.py      # demo FormDefinition (contactform) built in Python, tests load/render/validate
```

---

## `form_field.py` - lod_storable dataclasses

```python
@lod_storable
class FormField:
    name: str
    field_type: str          # text | textarea | select | hidden
    label: Optional[str] = None
    placeholder: Optional[str] = None
    glyphicon: Optional[str] = None
    required: bool = False
    error_msg: Optional[str] = None
    value: Optional[str] = None       # for hidden fields
    choices: Optional[List[str]] = None  # for select fields

@lod_storable
class FormDefinition:
    name: str
    legend: str
    fields: List[FormField]
    action: str = ""
    submit_label: str = "Absenden"
    submit_glyphicon: Optional[str] = None
    success_message: Optional[str] = None
```

Load with: `FormDefinition.load_from_yaml_file("/path/to/form.yaml")`

---

## `renderer.py` - Bootstrap 3 renderer adapted from wtforms-bootstrap5

Adapted from `wtforms_bootstrap5/renderers.py`. Key difference: targets Bootstrap 3 class names instead of Bootstrap 5.

`FormRenderer.render(form_def, values=None, errors=None) -> str`

Each visible field renders the Bootstrap 3 pattern:
```
div.form-group.has-feedback
  label.col-md-3.control-label.bitplanorange
  div.col-md-6.inputGroupContainer
    div.input-group
      span.input-group-addon > i.glyphicon.<glyphicon>
      input|textarea|select.form-control[data-bv-field]
    small[data-bv-validator] per validator
```

Hidden fields emit bare `<input type="hidden">`. No Jinja2 - pure Python string/Markup building via `markupsafe`.

---

## `handler.py` - POST validation

`FormHandler.validate(form_def, post_data) -> dict[str, list[str]]`
- Checks `required` fields
- Validates captcha via `expected` hidden field
- Generates/validates `postToken`

---

## `htmlfilter.py` changes

`MediaWikiHtmlFilter` gains an optional `form_registry: Optional[FormRegistry] = None` constructor parameter. `filter_html()` detects `<div class="wikicms-form" data-form-name="...">` and replaces it with rendered form HTML when `form_registry` is set.

`FormRegistry` is a singleton: `FormRegistry.register()`, `FormRegistry.register_from_yaml()` and `FormRegistry.get()` are class methods. The `form_registry` parameter passed to `MediaWikiHtmlFilter` is the `FormRegistry` class itself (not an instance).

---

## `webserver.py` changes

`CmsWebServer` accepts an optional `form_registry: Optional[FormRegistry] = None` that the deployer passes in at startup and forwards it to `MediaWikiHtmlFilter`.

---

## POST route

The deployer wires their own FastAPI POST route and calls `FormHandler.validate()`. The library does not auto-register routes.
