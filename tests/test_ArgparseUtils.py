"""
Argparse utilities unit tests

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

import os
import sys
import unittest

# Ensure the parent directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ArgparseUtils import RawDescriptionHelpFormatterWithLineWrap  # noqa: E402


class ArgparseUtilsTests(unittest.TestCase):

    def test_collapse_spaces_and_tabs(self):
        """Test that multiple spaces and tabs are collapsed into single spaces"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "This    is  a    test.\tThis\tis\ta\ttest."
        expected_output = "This is a test. This is a test."
        output = formatter._fill_text(input_text, 80, "")
        self.assertEqual(output, expected_output)

    def test_single_newlines_to_spaces(self):
        """Test that single newlines are converted to spaces"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "\nSentence one.\nSentence two.\n"
        expected_output = "Sentence one. Sentence two."
        output = formatter._fill_text(input_text, 80, "")
        self.assertEqual(output, expected_output)

    def test_multiple_newlines_preserved(self):
        """Test that multiple newlines are preserved as paragraph breaks"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "Paragraph one.\n\nParagraph two."
        expected_output = "Paragraph one.\n\nParagraph two."
        output = formatter._fill_text(input_text, 80, "")
        self.assertEqual(output, expected_output)

    def test_line_breaks_with_trailing_space(self):
        """Test that trailing spaces force line breaks"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "Line one with a trailing space. \nThis is the next line."
        expected_output = "Line one with a trailing space.\nThis is the next line."
        output = formatter._fill_text(input_text, 80, "")
        self.assertEqual(output, expected_output)

    def test_remove_spaces_after_newline(self):
        """Test that leading spaces after newlines are removed"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "Sentence one.\n    Sentence with leading spaces."
        expected_output = "Sentence one. Sentence with leading spaces."
        output = formatter._fill_text(input_text, 80, "")
        self.assertEqual(output, expected_output)

    def test_line_wrapping(self):
        """Test that long lines are wrapped"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "This is a very long line that should be wrapped appropriately by the formatter."
        expected_output = "This is a very long\nline that should be\nwrapped\nappropriately by the\nformatter."
        output = formatter._fill_text(input_text, 20, "")
        self.assertEqual(output, expected_output)

    def test_line_wrapping_with_indentation(self):
        """Test that indentation is applied and not subject to space collapsing"""
        formatter = RawDescriptionHelpFormatterWithLineWrap('unittest')
        input_text = "Testing for proper indention of the text."
        indent = " -  "
        expected_output = " -  Testing for\n -  proper indention\n -  of the text."
        output = formatter._fill_text(input_text, 20, indent)
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()
