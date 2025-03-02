"""
Graphlit API client for Nova.

This module provides a client for interacting with the Graphlit API.
"""

import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from nova.utils.logging import get_logger

logger = get_logger(__name__)


class GraphlitClient:
    """Client for interacting with the Graphlit API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client with optional API key.

        Args:
            api_key: The Graphlit API key. If not provided, it will be loaded from
                environment variables.
        """
        # Load environment variables if not already loaded
        load_dotenv()

        # Initialize API credentials
        self.organization_id = os.environ.get("GRAPHLIT_ORGANIZATION_ID")
        self.environment_id = os.environ.get("GRAPHLIT_ENVIRONMENT_ID")
        self.jwt_secret = api_key or os.environ.get("GRAPHLIT_JWT_SECRET")

        # Validate credentials
        if not self.organization_id:
            raise ValueError("GRAPHLIT_ORGANIZATION_ID environment variable is not set")
        if not self.environment_id:
            raise ValueError("GRAPHLIT_ENVIRONMENT_ID environment variable is not set")
        if not self.jwt_secret:
            raise ValueError("GRAPHLIT_JWT_SECRET environment variable is not set")

        # Initialize the client
        self.client = self._initialize_client()

        logger.info("GraphlitClient initialized successfully")

    def _initialize_client(self) -> Any:
        """Initialize the Graphlit client.

        Returns:
            The initialized Graphlit client.

        Note:
            This is a placeholder for the actual client initialization.
            In a real implementation, this would use the graphlit-client package.
        """
        # This is a placeholder for the actual client initialization
        # In a real implementation, this would use the graphlit-client package
        logger.debug("Initializing Graphlit client")
        return self

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: The GraphQL query to execute.
            variables: Optional variables for the query.

        Returns:
            The query result.
        """
        logger.debug(f"Executing GraphQL query: {query[:100]}...")

        # This is a placeholder for the actual query execution
        # In a real implementation, this would use the graphlit-client package

        # For now, we'll just make a direct HTTP request to the Graphlit API
        url = f"https://api.graphlit.com/organizations/{self.organization_id}/environments/{self.environment_id}/graphql"

        headers = {
            "Authorization": f"Bearer {self.jwt_secret}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "variables": variables or {},
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error executing GraphQL query: {str(e)}")
            raise

    def execute_mutation(self, mutation: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL mutation.

        Args:
            mutation: The GraphQL mutation to execute.
            variables: Optional variables for the mutation.

        Returns:
            The mutation result.
        """
        logger.debug(f"Executing GraphQL mutation: {mutation[:100]}...")

        # Mutations are just queries that modify data, so we can use the same method
        return self.execute_query(mutation, variables)
