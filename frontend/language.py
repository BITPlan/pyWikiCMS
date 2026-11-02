"""
Created on 2026-11-02

@author: wf
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LanguageSet:
    """
    the LanguageSet of a page: its master page and language code
    see https://github.com/BITPlan/pyWikiCMS/issues/39

    {{LanguageSet|master page=Willkommen|language=en}}
    {{Language|language=en}} has no master page
    """

    master_page: str = ""
    language: str = ""

    PATTERN = re.compile(r"{{Language(?:Set)?\|([^}]*)}}")

    @classmethod
    def from_markup(cls, markup: Optional[str]) -> Optional["LanguageSet"]:
        """
        parse the Language or LanguageSet template call of the given markup

        Args:
            markup(str): the wiki markup of a page

        Returns:
            LanguageSet: the set, None if the markup has no such template call
        """
        language_set = None
        if markup:
            match = cls.PATTERN.search(markup)
            if match:
                language_set = cls()
                for param in match.group(1).split("|"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key == "master page":
                            language_set.master_page = value
                        elif key == "language":
                            language_set.language = value
        return language_set


@dataclass
class VisitLanguage:
    """
    the language of a visit: chosen by the visitor, else the browser's,
    else the site default; the choice is held in a cookie for the visit
    see https://github.com/BITPlan/pyWikiCMS/issues/39
    """

    COOKIE = "lang"
    PARAM = "lang"

    languages: List[str] = field(default_factory=lambda: ["en"])
    default: str = "en"

    def accepted(self, accept_language: Optional[str]) -> Optional[str]:
        """
        the first language of the Accept-Language header the site offers

        Args:
            accept_language(str): the header value e.g. de-DE,de;q=0.9,en;q=0.8

        Returns:
            str: the language code, None if none is offered
        """
        language = None
        if accept_language:
            ranked = []
            for index, part in enumerate(accept_language.split(",")):
                tag, _, q = part.strip().partition(";q=")
                try:
                    quality = float(q) if q else 1.0
                except ValueError:
                    quality = 0.0
                code = tag.split("-")[0].strip().lower()
                ranked.append((-quality, index, code))
            for _, _, code in sorted(ranked):
                if code in self.languages:
                    language = code
                    break
        return language

    def resolve(
        self,
        param: Optional[str] = None,
        cookie: Optional[str] = None,
        accept_language: Optional[str] = None,
    ) -> str:
        """
        resolve the language of the visit

        Args:
            param(str): the lang query parameter, the visitor's choice
            cookie(str): the lang cookie, the choice held for the visit
            accept_language(str): the Accept-Language header of the browser

        Returns:
            str: the language code, always one the site offers
        """
        language = self.default
        for candidate in [param, cookie]:
            if candidate and candidate in self.languages:
                language = candidate
                break
        else:
            accepted = self.accepted(accept_language)
            if accepted:
                language = accepted
        return language

    def others(self, language: str) -> List[str]:
        """
        the languages the site offers besides the given one

        Args:
            language(str): the current language

        Returns:
            list[str]: the other language codes in site order
        """
        others = [code for code in self.languages if code != language]
        return others

    @staticmethod
    def switch_html(counterparts: Dict[str, str], prefix: str = "") -> str:
        """
        render the language switch: one link per other language to the
        counterpart of the current page

        Args:
            counterparts(dict): language code to page title of the counterpart
            prefix(str): the site prefix e.g. /www

        Returns:
            str: the nav html, empty without counterparts
        """
        html = ""
        if counterparts:
            lines = ['<nav class="menu-lang ms-auto text-nowrap">']
            for code, page_title in counterparts.items():
                page = page_title.replace(" ", "_")
                href = f"{prefix}/index.php/{page}?{VisitLanguage.PARAM}={code}"
                lines.append(
                    f'    <a hreflang="{code}" href="{href}">{code.upper()}</a>'
                )
            lines.append("</nav>")
            html = "\n".join(lines)
        return html
