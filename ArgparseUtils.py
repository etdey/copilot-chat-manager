"""
Argparse utilities

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

from __future__ import annotations  # for forward references in type hints

import argparse
import re
import textwrap


class RawDescriptionHelpFormatterWithLineWrap(argparse.HelpFormatter):
    """
    Custom argparse formatter for description and epilog that wraps lines like
    the default HelpFormatter, but treats newline kind of like markdown formatting.

    Rules:
    - Multiple space/tab characters are collapsed into a single space
    - Space prefixes for lines are removed
    - Single newlines are treated as spaces, unless they are preceded by a space
    - Multiple newlines are preserved as paragraph breaks

    If you want to force a line break, add a trailing space on the line.
    """

    def _fill_text(self, text, width, indent):
        textlines = []

        text = re.sub(r'[ \t]+', ' ', text)  # collapse multiple spaces/tabs
        text = re.sub(r'(?<=\n)[ \t]', '', text)  # remove spaces/tabs after newlines
        text = re.sub(r'(?<![ \n])\n(?!\n)', ' ', text)  # remove single, standalone newlines
        text = text.strip()

        for line in text.splitlines():
            line = line.strip()
            textlines.append(textwrap.fill(line, width,
                                           initial_indent=indent,
                                           subsequent_indent=indent))
        return "\n".join(textlines)
