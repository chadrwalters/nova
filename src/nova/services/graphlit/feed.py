"""
Feed management for Graphlit.

This module provides functionality for managing feeds in Graphlit.
"""

from typing import Any, Dict, List, Optional

from nova.services.graphlit.client import GraphlitClient
from nova.utils.logging import get_logger

logger = get_logger(__name__)


class FeedManager:
    """Manages Graphlit feeds."""

    def __init__(self, client: GraphlitClient):
        """Initialize with a Graphlit client.

        Args:
            client: The Graphlit client to use.
        """
        self.client = client
        logger.info("FeedManager initialized")

    def create_feed(self, name: str, description: Optional[str] = None) -> str:
        """Create a new feed and return its ID.

        Args:
            name: The name of the feed.
            description: Optional description of the feed.

        Returns:
            The ID of the created feed.
        """
        logger.info(f"Creating feed: {name}")

        result = self.client.execute_mutation("""
        mutation CreateFeed($name: String!, $description: String) {
          createFeed(input: {name: $name, description: $description}) {
            feed {
              id
              name
            }
          }
        }
        """, variables={
            "name": name,
            "description": description
        })

        feed_id = result["data"]["createFeed"]["feed"]["id"]
        logger.info(f"Created feed with ID: {feed_id}")

        return feed_id

    def list_feeds(self) -> List[Dict[str, Any]]:
        """List all available feeds.

        Returns:
            A list of feed objects.
        """
        logger.info("Listing feeds")

        result = self.client.execute_query("""
        query ListFeeds {
          feeds {
            edges {
              node {
                id
                name
                description
                createdAt
              }
            }
          }
        }
        """)

        feeds = [edge["node"] for edge in result["data"]["feeds"]["edges"]]
        logger.info(f"Found {len(feeds)} feeds")

        return feeds

    def get_feed(self, feed_id: str) -> Dict[str, Any]:
        """Get details of a specific feed.

        Args:
            feed_id: The ID of the feed to get.

        Returns:
            The feed details.
        """
        logger.info(f"Getting feed with ID: {feed_id}")

        result = self.client.execute_query("""
        query GetFeed($id: ID!) {
          feed(id: $id) {
            id
            name
            description
            createdAt
            contentCount
          }
        }
        """, variables={
            "id": feed_id
        })

        feed = result["data"]["feed"]
        logger.info(f"Retrieved feed: {feed['name']}")

        return feed

    def delete_feed(self, feed_id: str) -> bool:
        """Delete a feed.

        Args:
            feed_id: The ID of the feed to delete.

        Returns:
            True if the feed was deleted successfully, False otherwise.
        """
        logger.info(f"Deleting feed with ID: {feed_id}")

        result = self.client.execute_mutation("""
        mutation DeleteFeed($id: ID!) {
          deleteFeed(input: {id: $id}) {
            success
          }
        }
        """, variables={
            "id": feed_id
        })

        success = result["data"]["deleteFeed"]["success"]
        if success:
            logger.info(f"Successfully deleted feed with ID: {feed_id}")
        else:
            logger.warning(f"Failed to delete feed with ID: {feed_id}")

        return success
