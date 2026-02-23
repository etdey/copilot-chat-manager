"""
GitHub Copilot ChatSession object unit tests

Copyright (c) 2025 by Eric Dey. All rights reserved.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure the parent directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ChatSession import Chat  # noqa: E402


class SnapshotSessionTests(unittest.TestCase):
    def setUp(self):
        # Minimal valid session dict
        self.minimal_session_dict = {
            "requests": [
                {"message": {"text": "Hello"}, "response": [{"value": "World"}]}
            ]
        }
        self.minimal_session_str = json.dumps(self.minimal_session_dict)

    def test_init_with_dict(self):
        """Test Chat initializes with dict input"""
        chat = Chat(self.minimal_session_dict, lastUpdate=123.45)
        self.assertIsInstance(chat, Chat)
        self.assertEqual(chat.created, 123.45)
        self.assertEqual(chat.updated, 123.45)
        self.assertIsInstance(chat.requests, list)
        self.assertGreaterEqual(chat.size, 0)

    def test_init_with_str(self):
        """Test Chat initializes with JSON string input"""
        chat = Chat(self.minimal_session_str, lastUpdate=42.0)
        self.assertIsInstance(chat, Chat)
        self.assertEqual(chat.created, 42.0)
        self.assertEqual(chat.updated, 42.0)

    def test_init_with_invalid_type(self):
        """Test that invalid input type raises an exception"""
        with self.assertRaises(ValueError):
            Chat(12345)  # type: ignore[arg-type]

    def test_id_autogeneration(self):
        """Test that a stable ID is generated when no id is provided"""
        chat1 = Chat(self.minimal_session_dict)
        chat2 = Chat(self.minimal_session_dict)
        self.assertEqual(chat1.id, chat2.id)
        # Changing the input changes the hash
        altered = {"requests": [{"message": {"text": "Hi"}, "response": [{"value": "World"}]}]}
        chat3 = Chat(altered)
        self.assertNotEqual(chat1.id, chat3.id)

    def test_id_preservation(self):
        """Test that id is preserved when provided"""
        chat = Chat(self.minimal_session_dict, id="myid123")
        self.assertEqual(chat.id, "myid123")

    @patch("ChatSession.Request")
    def test_requests_parsing_and_size(self, mock_request):
        """Test that requests are parsed and size is computed"""
        # Mock Request to have a .size attribute
        mock_instance = MagicMock()
        mock_instance.size = 7
        mock_request.return_value = mock_instance
        session_dict = {"requests": [{"foo": "bar"}, {"baz": "qux"}]}
        chat = Chat(session_dict)
        self.assertEqual(len(chat.requests), 2)
        self.assertEqual(chat.size, 14)
        self.assertTrue(all(r is mock_instance for r in chat.requests))

    @patch("ChatSession.Request")
    def test_len_and_iter_methods(self, mock_request):
        """Test __len__ and __iter__ methods"""
        # Prepare two mock requests
        mock1 = MagicMock()
        mock1.request = "req1"
        mock1.response = "resp1"
        mock1.size = 5
        mock2 = MagicMock()
        mock2.request = "req2"
        mock2.response = "resp2"
        mock2.size = 8
        mock_request.side_effect = [mock1, mock2]
        session_dict = {"requests": [{}, {}]}
        chat = Chat(session_dict)
        self.assertEqual(len(chat), 2)
        items = list(iter(chat))
        self.assertEqual(items, [("req1", "resp1", 5), ("req2", "resp2", 8)])

    def test_sorting_attributes(self):
        """Test sorting_attributes static method"""
        attrs = Chat.sorting_attributes()
        self.assertIsInstance(attrs, list)
        self.assertGreater(len(attrs), 0)


class EventLogSessionTests(unittest.TestCase):

    def test_empty_content_returns_no_requests(self):
        """An empty JSONL file yields a Chat with no requests."""
        chat = _jsonl_chat_from_eventlog('')
        self.assertEqual(len(chat), 0)

    def test_invalid_first_event_raises(self):
        """A file whose first event is not kind:0 raises ValueError."""
        content = _jsonl_eventlog(
            _jsonl_append_line([_jsonl_request_dict()])
        )
        with self.assertRaises(ValueError):
            _jsonl_chat_from_eventlog(content)

    def test_unsupported_version_raises(self):
        """A kind:0 snapshot with an unrecognised version number raises ValueError."""
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(version=99)
        )
        with self.assertRaises(ValueError):
            _jsonl_chat_from_eventlog(content)

    def test_snapshot_requests_are_seeded(self):
        """Requests already in the kind:0 snapshot are included alongside newly appended ones."""
        existing = _jsonl_snapshot_request_dict(text='Old question', response_text='Old answer')
        new = _jsonl_request_dict(text='New question', response=[{'value': 'New answer'}])
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(requests=[existing]),
            _jsonl_append_line([new]),
        )
        chat = _jsonl_chat_from_eventlog(content)
        self.assertEqual(len(chat), 2)
        texts = [r[0] for r in chat]
        self.assertIn('Old question', texts)
        self.assertIn('New question', texts)

    def test_kind2_patch_sets_response(self):
        """A kind:2 event with k=['requests', N, 'response'] patches the response list directly.
        This is the primary path VS Code uses when the assistant's reply arrives."""
        req = _jsonl_request_dict()
        rich_response = [{'value': 'The real response text'}]
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(),
            _jsonl_append_line([req]),
            _jsonl_patch_line(0, 'response', rich_response, kind=2),
        )
        chat = _jsonl_chat_from_eventlog(content)
        self.assertEqual(len(chat), 1)
        _, resp_text, _ = list(chat)[0]
        self.assertIn('The real response text', resp_text)

    def test_kind1_result_patch_synthesizes_response_as_fallback(self):
        """When only a kind:1 result patch arrives, the response is synthesised from
        result.metadata.toolCallRounds[*].response (fallback path)."""
        req = _jsonl_request_dict()
        result_patch = {'metadata': {'toolCallRounds': [{'response': 'Synthesized response text'}]}}
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(),
            _jsonl_append_line([req]),
            _jsonl_patch_line(0, 'result', result_patch, kind=1),
        )
        chat = _jsonl_chat_from_eventlog(content)
        self.assertEqual(len(chat), 1)
        _, resp_text, _ = list(chat)[0]
        self.assertIn('Synthesized response text', resp_text)

    def test_multiple_toolcall_rounds_are_concatenated(self):
        """Multiple toolCallRounds entries are concatenated in order with a tool-name
        annotation inserted between rounds so the reader can follow the conversation flow."""
        req = _jsonl_request_dict()
        result_patch = {
            'metadata': {
                'toolCallRounds': [
                    {'response': 'First part. ', 'toolCalls': [{'name': 'run_in_terminal', 'id': 't1', 'arguments': ''}]},
                    {'response': 'Second part.', 'toolCalls': []},
                ]
            }
        }
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(),
            _jsonl_append_line([req]),
            _jsonl_patch_line(0, 'result', result_patch, kind=1),
        )
        chat = _jsonl_chat_from_eventlog(content)
        _, resp_text, _ = list(chat)[0]
        self.assertIn('First part.', resp_text)
        self.assertIn('run_in_terminal', resp_text)
        self.assertIn('Second part.', resp_text)
        self.assertLess(resp_text.index('First part.'), resp_text.index('run_in_terminal'))
        self.assertLess(resp_text.index('run_in_terminal'), resp_text.index('Second part.'))

    def test_malformed_entries_removed_and_indices_stay_aligned(self):
        """Malformed kind:2 entries are stored as index-preserving placeholders during replay
        so that patch back-references land on the right request, then placeholders are stripped."""
        malformed = {'timestamp': 1_000_000}          # missing requestId and message
        valid_req = _jsonl_request_dict(text='Valid question')
        rich_response = [{'value': 'Aligned response'}]
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(),
            _jsonl_append_line([malformed, valid_req]),    # malformed→index 0, valid→index 1
            _jsonl_patch_line(1, 'response', rich_response, kind=2),
        )
        chat = _jsonl_chat_from_eventlog(content)
        self.assertEqual(len(chat), 1)               # placeholder removed
        _, resp_text, _ = list(chat)[0]
        self.assertIn('Aligned response', resp_text)

    def test_toplevel_kind1_patches_are_ignored(self):
        """Top-level kind:1 state patches (e.g. inputState) do not affect request parsing."""
        req = _jsonl_request_dict(text='Hello', response=[{'value': 'World'}])
        content = _jsonl_eventlog(
            _jsonl_snapshot_line(),
            _jsonl_toplevel_patch_line('inputState', {'inputText': 'typing...'}),
            _jsonl_append_line([req]),
            _jsonl_toplevel_patch_line('inputState', {'inputText': ''}),
        )
        chat = _jsonl_chat_from_eventlog(content)
        self.assertEqual(len(chat), 1)
        req_text, resp_text, _ = list(chat)[0]
        self.assertEqual(req_text, 'Hello')
        self.assertIn('World', resp_text)


# 
# JSONL event-log test helper functions
# 

def _jsonl_snapshot_line(requests=None, version=3, creation_date=1_000_000):
    """kind:0 snapshot event — the mandatory first line of every .jsonl file."""
    return json.dumps({
        'kind': 0,
        'v': {
            'version': version,
            'creationDate': creation_date,
            'requests': requests if requests is not None else [],
        }
    })


def _jsonl_append_line(req_list):
    """kind:2 event without a 'k' key — appends new request objects to the session."""
    return json.dumps({'kind': 2, 'v': req_list})


def _jsonl_patch_line(index, field, value, kind=1):
    """kind:1 or kind:2 patch event — sets requests[index][field] = value."""
    return json.dumps({'kind': kind, 'k': ['requests', index, field], 'v': value})


def _jsonl_toplevel_patch_line(field, value):
    """kind:1 patch to a top-level key (e.g. inputState) — should be ignored by the parser."""
    return json.dumps({'kind': 1, 'k': [field], 'v': value})


def _jsonl_request_dict(text='Hello', response=None, req_id='req-001', timestamp=2_000_000):
    """Minimal valid request dict as it appears in a kind:2 append event."""
    return {
        'requestId': req_id,
        'timestamp': timestamp,
        'message': {'text': text},
        'response': response if response is not None
                    else [{'kind': 'mcpServersStarting', 'didStartServerIds': []}],
    }


def _jsonl_snapshot_request_dict(text='Snapshot question', response_text='Snapshot answer', req_id='snap-req-001'):
    """Minimal request dict suitable for embedding in the kind:0 snapshot's requests list."""
    return {
        'requestId': req_id,
        'timestamp': 500_000,
        'message': {'text': text},
        'response': [{'value': response_text}],
    }


def _jsonl_eventlog(*lines):
    """Join event-line strings into a complete JSONL document."""
    return '\n'.join(lines) + '\n'


def _jsonl_chat_from_eventlog(content):
    """Write content to a temp .jsonl file and return the parsed Chat instance."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp_path = f.name
    try:
        return Chat(tmp_path)
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
