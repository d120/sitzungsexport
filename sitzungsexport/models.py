import re
from typing import List, Optional, Dict
from datetime import date
from dataclasses import dataclass
from email.parser import HeaderParser

from sitzungsexport import replacements

from sentry_sdk import configure_scope #type: ignore


class Protocol:
    BTEIL_REG = "<[bB]-?[tT]eil[^>]*>(.*?)<.?[bB]-?[tT]eil>"
    REPLACEMENT_PATTERN = "<BOOKSTACK-B-{}>"

    def __init__(self, text: str, preview: bool = False):
        with configure_scope() as scope:
            scope.set_extra("protocol", text)
        self.__text = text
        split = self.__text.split("---\n", 2)
        self.yaml = split[1]
        self.text = split[2]
        # remove all whitespace before the tops start
        self.text = self.text[self.text.find("#") :]
        # find all bteile as strings
        self.bteile: List[Bteil] = []
        if not preview:
            bteil_regex = re.compile(self.BTEIL_REG, flags=re.S | re.M | re.IGNORECASE)
            bteile_matches = bteil_regex.finditer(self.text)
            for i, bteil_match in enumerate(bteile_matches):
                self.text = self.text.replace(
                    bteil_match[0], self.REPLACEMENT_PATTERN.format(i)
                )
                self.bteile.append(Bteil(content=bteil_match[1]))
        self.frontmatter = dict(HeaderParser().parsestr(self.yaml)) # type: ignore

    @property
    def bteil_count(self) -> int:
        return len(self.bteile)

    def compile(self) -> str:
        output = self.text
        for i, bteil in enumerate(self.bteile):
            output = output.replace(
                self.REPLACEMENT_PATTERN.format(i), bteil.replacement # type: ignore

            )
        output = replacements.vote(output)
        output = replacements.gendern(output)
        output = replacements.frontmatter(output, **self.frontmatter)
        output = replacements.fix_indentation(output)
        return output


@dataclass
class Bteil:
    content: str
    replacement: Optional[str] = None
