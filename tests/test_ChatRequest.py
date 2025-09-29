"""
GitHub Copilot Chat Request object unit tests

Copyright (c) 2025 by Eric Dey. All rights reserved.

"""

import unittest
from unittest.mock import patch as unittest_mock_patch
import json, os, sys

# Ensure the parent directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ChatRequest import Request, ChatRequestParseError, ChatRequestEmptyRequest, ChatRequestCanceled, SKIPPED_RESPONSE_KINDS

class ChatRequestTests(unittest.TestCase):
    
    def test_basic_request_response(self):
        """Basic request and response parsing with single and multiple response blocks"""
        responses = [ {"value": "World"}, {"value": "And"}, {"value": "Universe"} ]
        input_json = { "message": {"text": "Hello"}, "response": [] }
        for i in range(len(responses)):
            with self.subTest(msg=f"{i} response blocks", i=i, input_json=input_json, responses=responses):
                input_json['response'] = responses[:i+1]
                expected_response = "".join([r["value"] for r in responses[:i+1]])
                req = Request(input_json)
                self.assertEqual(req.request, "Hello")
                self.assertEqual(expected_response, req.response)
                self.assertGreater(req.size, len(expected_response))

    def test_empty_requests_error(self):
        """Check that empty request prompts raise exception"""
        input_json = {
            "message": {"text": ""},
            "response": [{"value": "no request was made"}]
        }
        with self.assertRaises(ChatRequestEmptyRequest):
            Request(input_json)

    def test_is_canceled_error(self):
        """Check that canceled requests raise exception"""
        input_json = {
            "isCanceled": True,
            "message": {"text": "Should not matter"},
            "response": []
        }
        with self.assertRaises(ChatRequestCanceled):
            Request(input_json)

    def test_string_input(self):
        """Check that string JSON can be used instead of dict"""
        input_dict = {
            "message": {"text": "Test string input"},
            "response": [
                {"value": "String input works"}
            ]
        }
        input_str = json.dumps(input_dict)
        req = Request(input_str)
        self.assertEqual(req.request, "Test string input")
        self.assertIn("String input works", req.response)

    def test_invalid_input_type_error(self):
        """Check that input types other than str|dict raise exception"""
        with self.assertRaises(ValueError):
            Request(123)  # type: ignore[arg-type]

    def test_no_response(self):
        """Check that no response is handled correctly"""
        input_json = {
            "message": {"text": "No response"},
            "response": []
        }
        req = Request(input_json)
        self.assertEqual(req.response, "")
        self.assertEqual(req.rawResponse, "[]")

    def test_textEditGroup_path(self):
        """Check that textEditGroup responses are parsed correctly"""
        input_json = {
            "message": {"text": "Edit file"},
            "response": [
                {
                    "kind": "textEditGroup",
                    "uri": {"fsPath": "file.py"},
                    "edits": [
                        [
                            {
                                "text": "new text",
                                "range": {"startLineNumber": 1, "endLineNumber": 2}
                            },
                            {
                                "text": "",
                                "range": {"startLineNumber": 3, "endLineNumber": 4}
                            }
                        ]
                    ]
                }
            ]
        }
        req = Request(input_json)
        self.assertIn("Edited file: `file.py`", req.response)
        self.assertIn(" added ", req.response)
        self.assertIn(" deleted ", req.response)

    def test_textEditGroup_parse_error(self):
        """Check that malformed textEditGroup responses raise parse errors"""
        bad_edits_objs = [
            ("Missing 'text' key", {"range": {"startLineNumber": 1, "endLineNumber": 1}}),
            ("Missing 'range' key", {"text": "new text"}),
            ("Range missing 'startLineNumber'", {"text": "new text", "range": {"endLineNumber": 1}}),
            ("Range missing 'endLineNumber'", {"text": "new text", "range": {"startLineNumber": 1}}),
            ("Range not a dict", {"text": "new text", "range": "not a dict"}),
            ("Edit not a dict", "not a dict"),
        ]
        for test_case, bad_edit in bad_edits_objs:
            with self.subTest(msg=test_case, bad_edit=bad_edit):
                input_json = {
                    "message": {"text": "Edit file"},
                    "response": [
                        {
                            "kind": "textEditGroup",
                            "uri": {"fsPath": "file.py"},
                            "edits": [
                                [ bad_edit ]
                            ]
                        }
                    ]
                }
                with self.assertRaises(ChatRequestParseError):
                    Request(input_json)

    def test_inlineReference_path(self):
        """Check for proper parsing and quoting of inlineReference types"""
        references = [
            ("File path", {"fsPath": "ref_string"}),
            ("Method name", {"name": "ref_string"}),
        ]
        for desc, ref in references:
            with self.subTest(msg=f"{desc} reference", ref=ref):
                input_json = {
                    "message": {"text": "Reference"},
                    "response": [
                        {"value": "Reference "},
                        {"kind": "inlineReference", "inlineReference": ref},
                        {"value": " is here"},
                    ]
                }
                req = Request(input_json)
                self.assertIn("Reference `ref_string` is here", req.response)

    def test_skipped_response_kind(self):
        """Check that non-handled response kinds are skipped"""
        for kind in SKIPPED_RESPONSE_KINDS:
            with self.subTest(msg=f"{kind} response", kind=kind):
                input_json = {
                    "message": {"text": f"Skip kind {kind}"},
                    "response": [
                        {"kind": kind, "value": "should be skipped"}
                    ]
                }
                req = Request(input_json)
                self.assertNotIn("should be skipped", req.response)

    def test_unhandled_response_kind(self):
        """Check that unhandled, unexpected response kinds are logged and skipped"""
        input_json = {
            "message": {"text": "Unhandled kind"},
            "response": [
                {"kind": "unknownKind", "value": "unknown"}
            ]
        }
        with unittest_mock_patch('ChatRequest.Log.info') as mock_log_info:
            req = Request(input_json)
            self.assertNotIn("unknown", req.response)
            mock_log_info.assert_called_once_with("skipping unhandled response kind: unknownKind")


if __name__ == "__main__":
    unittest.main()
