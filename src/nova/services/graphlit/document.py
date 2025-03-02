"""
Document management for Graphlit.

This module provides functionality for managing document uploads to Graphlit.
"""

import os
from typing import Any, Dict, List, Optional

from nova.services.graphlit.client import GraphlitClient
from nova.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentManager:
    """Manages document uploads to Graphlit."""

    def __init__(self, client: GraphlitClient):
        """Initialize with a Graphlit client.

        Args:
            client: The Graphlit client to use.
        """
        self.client = client
        logger.info("DocumentManager initialized")

    def upload_markdown(self, feed_id: str, file_path: str, name: Optional[str] = None) -> str:
        """Upload a markdown file to a feed and return the content ID.

        Args:
            feed_id: The ID of the feed to upload to.
            file_path: The path to the markdown file.
            name: Optional name for the content. If not provided, the file name will be used.

        Returns:
            The ID of the uploaded content.
        """
        file_name = os.path.basename(file_path)
        content_name = name or file_name

        logger.info(f"Uploading markdown file: {file_path} to feed: {feed_id}")

        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Upload the content
        result = self.client.execute_mutation("""
        mutation IngestText($feedId: ID!, $name: String!, $content: String!) {
          ingestText(input: {
            feedId: $feedId,
            name: $name,
            text: $content,
            contentType: "text/markdown"
          }) {
            content {
              id
              name
            }
          }
        }
        """, variables={
            "feedId": feed_id,
            "name": content_name,
            "content": content
        })

        content_id = result["data"]["ingestText"]["content"]["id"]
        logger.info(f"Successfully uploaded {file_name} with ID: {content_id}")

        return content_id

    def upload_batch(self, feed_id: str, file_paths: List[str]) -> List[str]:
        """Upload multiple markdown files and return content IDs.

        Args:
            feed_id: The ID of the feed to upload to.
            file_paths: The paths to the markdown files.

        Returns:
            A list of content IDs for the uploaded files.
        """
        logger.info(f"Batch uploading {len(file_paths)} files to feed: {feed_id}")

        content_ids = []
        for file_path in file_paths:
            try:
                content_id = self.upload_markdown(feed_id, file_path)
                content_ids.append(content_id)
            except Exception as e:
                logger.error(f"Error uploading {os.path.basename(file_path)}: {str(e)}")

        logger.info(f"Successfully uploaded {len(content_ids)}/{len(file_paths)} files")

        return content_ids

    def search_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for content using Graphlit's semantic search.

        Args:
            query: The search query.
            limit: The maximum number of results to return.

        Returns:
            A list of content objects matching the query.
        """
        logger.info(f"Searching for content with query: {query}")

        result = self.client.execute_query("""
        query SearchContent($query: String!, $first: Int!) {
          semanticSearch(query: $query, first: $first) {
            edges {
              node {
                id
                name
                text
                score
              }
            }
          }
        }
        """, variables={
            "query": query,
            "first": limit
        })

        content = [edge["node"] for edge in result["data"]["semanticSearch"]["edges"]]
        logger.info(f"Found {len(content)} results for query: {query}")

        return content

    def get_content(self, content_id: str) -> Dict[str, Any]:
        """Get details of a specific content item.

        Args:
            content_id: The ID of the content to get.

        Returns:
            The content details.
        """
        logger.info(f"Getting content with ID: {content_id}")

        result = self.client.execute_query("""
        query GetContent($id: ID!) {
          content(id: $id) {
            id
            name
            text
            contentType
            createdAt
            updatedAt
          }
        }
        """, variables={
            "id": content_id
        })

        content = result["data"]["content"]
        logger.info(f"Retrieved content: {content['name']}")

        return content

    def delete_content(self, content_id: str) -> bool:
        """Delete a content item.

        Args:
            content_id: The ID of the content to delete.

        Returns:
            True if the content was deleted successfully, False otherwise.
        """
        logger.info(f"Deleting content with ID: {content_id}")

        result = self.client.execute_mutation("""
        mutation DeleteContent($id: ID!) {
          deleteContent(input: {id: $id}) {
            success
          }
        }
        """, variables={
            "id": content_id
        })

        success = result["data"]["deleteContent"]["success"]
        if success:
            logger.info(f"Successfully deleted content with ID: {content_id}")
        else:
            logger.warning(f"Failed to delete content with ID: {content_id}")

        return success
