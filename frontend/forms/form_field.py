"""
Created on 2026-03-30

@author: wf
"""

from typing import List, Optional

from basemkit.yamlable import lod_storable


@lod_storable
class FormField:
    """
    A single field in a form definition.
    """

    name: str
    field_type: str  # text | textarea | select | hidden
    label: Optional[str] = None
    placeholder: Optional[str] = None
    glyphicon: Optional[str] = None
    required: bool = False
    error_msg: Optional[str] = None
    value: Optional[str] = None  # for hidden fields
    choices: Optional[List[str]] = None  # for select fields


@lod_storable
class FormDefinition:
    """
    A complete form definition with all fields and metadata.
    """

    name: str
    legend: str
    fields: List[FormField]
    action: str = ""
    submit_label: str = "Absenden"
    submit_glyphicon: Optional[str] = None
    success_message: Optional[str] = None
