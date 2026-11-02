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
            str: the html; a section with a single entry is a plain link,
            a section with more entries is a details element with the section label as summary
        """
        lines = ['<nav class="menu">']
        for section in self.sections:
            if len(section.entries) == 1:
                entry = section.entries[0]
                lines.append(f'  <a href="{entry.href(prefix)}">{entry.label}</a>')
            elif section.entries:
                lines.append("  <details>")
                lines.append(f"    <summary>{section.label}</summary>")
                lines.append("    <ul>")
                for entry in section.entries:
                    lines.append(
                        f'      <li><a href="{entry.href(prefix)}">{entry.label}</a></li>'
                    )
                lines.append("    </ul>")
                lines.append("  </details>")
        lines.append("</nav>")
        html = "\n".join(lines)
        return html
