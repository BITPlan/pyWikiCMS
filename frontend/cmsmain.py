"""
Created on 2022-11-24

@author: wf
"""

import os
import sys
from argparse import ArgumentParser

from ngwidgets.cmd import WebserverCmd

from frontend.forms.registry import FormRegistry
from frontend.webserver import CmsWebServer

DEFAULT_FORMS_DIR = os.path.expanduser("~/.wikicms/forms")


class CmsMain(WebserverCmd):
    """
    ContentManagement System Main Program
    """

    def getArgParser(self, description: str, version_msg) -> ArgumentParser:
        """
        override the default argparser call
        """
        parser = super().getArgParser(description, version_msg)
        parser.add_argument(
            "--server", help="optional server to work with e.g. for debugging"
        )
        parser.add_argument(
            "--sites",
            nargs="+",
            required=False,
            help="space-separated list of sites (or use comma-separated string)",
        )
        parser.add_argument(
            "--forms",
            default=DEFAULT_FORMS_DIR,
            help=f"directory containing form YAML files (default: {DEFAULT_FORMS_DIR})",
        )
        return parser

    def _load_forms(self, forms_dir: str) -> FormRegistry:
        """
        Load all *.yaml files from forms_dir into the FormRegistry.

        Args:
            forms_dir(str): path to directory containing form YAML files

        Returns:
            FormRegistry: the populated singleton registry
        """
        registry = FormRegistry.instance()
        if os.path.isdir(forms_dir):
            for fname in sorted(os.listdir(forms_dir)):
                if fname.endswith(".yaml"):
                    yaml_path = os.path.join(forms_dir, fname)
                    FormRegistry.register_from_yaml(yaml_path)
        return registry

    def cmd_main(self, argv=None):
        """
        override cmd_main to load forms before starting the webserver
        """
        exit_code = super().cmd_main(argv)
        return exit_code


def main(argv: list = None):
    """
    main call
    """
    cmd = CmsMain(config=CmsWebServer.get_config(), webserver_cls=CmsWebServer)
    # Parse args early to get forms dir before webserver starts
    args, _ = cmd.parser.parse_known_args(argv)
    forms_dir = getattr(args, "forms", DEFAULT_FORMS_DIR)
    form_registry = cmd._load_forms(forms_dir)
    # Patch webserver class to receive form_registry at construction
    original_init = CmsWebServer.__init__

    def patched_init(self, **kwargs):
        original_init(self, form_registry=form_registry, **kwargs)

    CmsWebServer.__init__ = patched_init
    exit_code = cmd.cmd_main(argv)
    return exit_code


DEBUG = 0
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-d")
    sys.exit(main())
