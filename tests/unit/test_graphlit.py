"""
Unit tests for the Graphlit integration.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from nova.services.graphlit.client import GraphlitClient
from nova.services.graphlit.feed import FeedManager
from nova.services.graphlit.document import DocumentManager


class TestGraphlitClient(unittest.TestCase):
    """Test the GraphlitClient class."""

    @patch.dict(os.environ, {
        "GRAPHLIT_ORGANIZATION_ID": "test_org_id",
        "GRAPHLIT_ENVIRONMENT_ID": "test_env_id",
        "GRAPHLIT_JWT_SECRET": "test_jwt_secret"
    })
    def test_init(self):
        """Test initialization of the GraphlitClient."""
        client = GraphlitClient()
        self.assertEqual(client.organization_id, "test_org_id")
        self.assertEqual(client.environment_id, "test_env_id")
        self.assertEqual(client.jwt_secret, "test_jwt_secret")

    @patch.dict(os.environ, {})
    def test_init_missing_env_vars(self):
        """Test initialization with missing environment variables."""
        with self.assertRaises(ValueError):
            GraphlitClient()

    @patch.dict(os.environ, {
        "GRAPHLIT_ORGANIZATION_ID": "test_org_id",
        "GRAPHLIT_ENVIRONMENT_ID": "test_env_id",
        "GRAPHLIT_JWT_SECRET": "test_jwt_secret"
    })
    @patch("requests.post")
    def test_execute_query(self, mock_post):
        """Test executing a GraphQL query."""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_post.return_value = mock_response

        # Execute the query
        client = GraphlitClient()
        result = client.execute_query("query { test }")

        # Check the result
        self.assertEqual(result, {"data": {"test": "value"}})

        # Check that the request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["query"], "query { test }")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test_jwt_secret")


class TestFeedManager(unittest.TestCase):
    """Test the FeedManager class."""

    def setUp(self):
        """Set up the test."""
        self.client = MagicMock()
        self.feed_manager = FeedManager(self.client)

    def test_create_feed(self):
        """Test creating a feed."""
        # Set up the mock response
        self.client.execute_mutation.return_value = {
            "data": {
                "createFeed": {
                    "feed": {
                        "id": "feed_123",
                        "name": "Test Feed"
                    }
                }
            }
        }

        # Create the feed
        feed_id = self.feed_manager.create_feed("Test Feed", "Test Description")

        # Check the result
        self.assertEqual(feed_id, "feed_123")

        # Check that the mutation was executed correctly
        self.client.execute_mutation.assert_called_once()
        args, kwargs = self.client.execute_mutation.call_args
        self.assertIn("CreateFeed", args[0])
        self.assertEqual(kwargs["variables"]["name"], "Test Feed")
        self.assertEqual(kwargs["variables"]["description"], "Test Description")


class TestDocumentManager(unittest.TestCase):
    """Test the DocumentManager class."""

    def setUp(self):
        """Set up the test."""
        self.client = MagicMock()
        self.document_manager = DocumentManager(self.client)

    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="# Test Content")
    def test_upload_markdown(self, mock_open):
        """Test uploading a markdown file."""
        # Set up the mock response
        self.client.execute_mutation.return_value = {
            "data": {
                "ingestText": {
                    "content": {
                        "id": "content_123",
                        "name": "test.md"
                    }
                }
            }
        }

        # Upload the markdown file
        content_id = self.document_manager.upload_markdown("feed_123", "/path/to/test.md")

        # Check the result
        self.assertEqual(content_id, "content_123")

        # Check that the file was opened correctly
        mock_open.assert_called_once_with("/path/to/test.md", "r", encoding="utf-8")

        # Check that the mutation was executed correctly
        self.client.execute_mutation.assert_called_once()
        args, kwargs = self.client.execute_mutation.call_args
        self.assertIn("IngestText", args[0])
        self.assertEqual(kwargs["variables"]["feedId"], "feed_123")
        self.assertEqual(kwargs["variables"]["name"], "test.md")
        self.assertEqual(kwargs["variables"]["content"], "# Test Content")


if __name__ == "__main__":
    unittest.main()
