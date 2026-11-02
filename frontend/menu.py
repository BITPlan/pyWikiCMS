"""
Created on 2026-11-02

@author: wf
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MenuEntry:
    """
    one entry of a menu section
    """

    target: str
    label: str

    def href(self, prefix: str) -> str:
        """
        get the href for this entry

        Args:
            prefix(str): the site prefix e.g. /www

        Returns:
            str: an external url unchanged, a page target as index.php path
        """
        if "://" in self.target:
            href = self.target
        else:
            page = self.target.replace(" ", "_")
            href = f"{prefix}/index.php/{page}"
        return href


@dataclass
class MenuSection:
    """
    a section of a menu with a label and entries
    """

    label: str
    entries: List[MenuEntry] = field(default_factory=list)


@dataclass
class Menu:
    """
    site navigation in MediaWiki:Sidebar syntax

    * section
    ** target|label
    """

    sections: List[MenuSection] = field(default_factory=list)

    @classmethod
    def from_markup(cls, markup: Optional[str]) -> "Menu":
        """
        parse the given sidebar markup

        Args:
            markup(str): the wiki markup of a MediaWiki:Menu or MediaWiki:Sidebar page

        Returns:
            Menu: the parsed menu
        """
        menu = cls()
        section = None
        for line in (markup or "").splitlines():
            line = line.strip()
            if line.startswith("**"):
                if section is not None:
                    entry_text = line[2:].strip()
                    if "|" in entry_text:
                        target, label = entry_text.split("|", 1)
                    else:
                        target, label = entry_text, entry_text
                    section.entries.append(MenuEntry(target.strip(), label.strip()))
            elif line.startswith("*"):
                section = MenuSection(label=line[1:].strip())
                menu.sections.append(section)
        return menu

    def as_html(self, prefix: str = "") -> str:
        """
        render the menu as a nav element without script

        Args:
            prefix(str): the site prefix e.g. /www

        Returns:
            str: the html with two forms of the same sections and no script:
            a bar from the medium breakpoint up with the section terms inline,
            the last section at the right edge, and below the breakpoint one
            details element with ☰ as summary, the hamburger, holding all
            sections as a list; a section with a single entry is that entry's
            link, a section with more entries is its label with the entries
            as a dropdown
        """
        html = self.hamburger_html(prefix) + "\n" + self.bar_html(prefix)
        return html

    def hamburger_html(self, prefix: str = "") -> str:
        """
        the hamburger form, placed left of the logo as in the former Menu.rythm

        Args:
            prefix(str): the site prefix

        Returns:
            str: the html, empty without sections
        """
        html = ""
        if self.sections:
            html = "\n".join(self.hamburger_lines(prefix))
        return html

    def bar_html(self, prefix: str = "") -> str:
        """
        the bar form, placed right of the logo

        Args:
            prefix(str): the site prefix

        Returns:
            str: the html, empty without sections
        """
        html = ""
        if self.sections:
            html = "\n".join(self.bar_lines(prefix))
        return html

    SUMMARY_STYLE = 'style="list-style:none;cursor:pointer"'
    DROPDOWN = (
        "list-unstyled text-nowrap text-start position-absolute bg-white shadow p-3 m-0"
    )

    def bar_lines(self, prefix: str) -> List[str]:
        """
        the bar form for the medium breakpoint and up

        Args:
            prefix(str): the site prefix

        Returns:
            list[str]: html lines
        """
        lines = [
            '<nav class="menu-bar d-none d-md-flex align-items-center gap-4 ms-4 flex-grow-1">'
        ]
        filled = [section for section in self.sections if section.entries]
        last = len(filled) - 1
        for index, section in enumerate(filled):
            edge = " ms-auto" if index == last and index > 0 else ""
            if len(section.entries) == 1:
                entry = section.entries[0]
                lines.append(
                    f'    <a class="text-nowrap{edge}" href="{entry.href(prefix)}">{entry.label}</a>'
                )
            elif section.entries:
                lines.append(f'    <details class="position-relative{edge}">')
                lines.append(
                    f"      <summary {self.SUMMARY_STYLE}>{section.label}</summary>"
                )
                lines.append(f'      <ul class="{self.DROPDOWN} start-0">')
                for entry in section.entries:
                    lines.append(
                        f'        <li><a href="{entry.href(prefix)}">{entry.label}</a></li>'
                    )
                lines.append("      </ul>")
                lines.append("    </details>")
        lines.append("</nav>")
        return lines

    def hamburger_lines(self, prefix: str) -> List[str]:
        """
        the hamburger form below the medium breakpoint

        Args:
            prefix(str): the site prefix

        Returns:
            list[str]: html lines
        """
        lines = ['<nav class="menu-hamburger d-md-none me-3">']
        lines.append('    <details class="position-relative">')
        lines.append(
            f'      <summary aria-label="menu" class="fs-2" {self.SUMMARY_STYLE}>☰</summary>'
        )
        lines.append(f'      <ul class="{self.DROPDOWN} start-0">')
        for section in self.sections:
            if len(section.entries) == 1:
                entry = section.entries[0]
                lines.append(
                    f'        <li><a href="{entry.href(prefix)}">{entry.label}</a></li>'
                )
            elif section.entries:
                lines.append(f"        <li>{section.label}")
                lines.append('          <ul class="list-unstyled ps-3">')
                for entry in section.entries:
                    lines.append(
                        f'            <li><a href="{entry.href(prefix)}">{entry.label}</a></li>'
                    )
                lines.append("          </ul>")
                lines.append("        </li>")
        lines.append("      </ul>")
        lines.append("    </details>")
        lines.append("</nav>")
        return lines
