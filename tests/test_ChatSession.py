"""
GitHub Copilot ChatSession object unit tests

Copyright (c) 2025 by Eric Dey. All rights reserved.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure the parent directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ChatSession import Chat  # noqa: E402


class ChatSessionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
