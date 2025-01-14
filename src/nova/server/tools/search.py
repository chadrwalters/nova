"""Search tool implementation."""

from pathlib import Path
from typing import Any, TypedDict

import numpy as np
from jsonschema.validators import validate

from nova.server.tools.base import ToolHandler
from nova.server.types import ResourceError, ToolMetadata, ToolType
from nova.vector_store.store import VectorStore


class SearchRequest(TypedDict, total=False):
    """Search request type."""

    query: str
    n_results: int
    min_score: float
    filters: dict[str, Any]


class SearchResult(TypedDict):
    """Search result type."""

    id: str
    score: float
    content: str
    metadata: dict[str, Any]


class SearchTool(ToolHandler):
    """Tool for searching vector store."""

    def __init__(self, schema_path: Path, vector_store: VectorStore) -> None:
        """Initialize search tool.

        Args:
            schema_path: Path to schema file
            vector_store: Vector store instance to search
        """
        super().__init__(schema_path)
        self._store = vector_store

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return {
            "id": "search",
            "type": ToolType.SEARCH,
            "name": "Search Tool",
            "version": "0.1.0",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "required": True,
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "required": False,
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum similarity score",
                    "required": False,
                },
            },
            "capabilities": ["search"],
        }

    def validate_request(self, request: dict[str, Any]) -> None:
        """Validate search request.

        Args:
            request: Search request dictionary

        Raises:
            ResourceError: If request is invalid
        """
        try:
            # Extract parameters from request
            parameters = request.get("parameters", {})
            if not isinstance(parameters, dict):
                raise ValueError("Invalid parameters")

            # Extract and validate query
            query = parameters.get("query")
            if not query or not isinstance(query, str):
                raise ResourceError(
                    "Invalid search request: 'query' is a required property"
                )

            # Validate numeric fields
            n_results = parameters.get("n_results", 10)
            if not isinstance(n_results, int) or n_results < 1:
                raise ValueError("Invalid n_results")

            min_score = parameters.get("min_score", 0.0)
            if (
                not isinstance(min_score, (int, float))
                or min_score < 0
                or min_score > 1
            ):
                raise ValueError("Invalid min_score")

            # Validate filters if present
            filters = parameters.get("filters")
            if filters is not None and not isinstance(filters, dict):
                raise ValueError("Invalid filters")

            # Validate against schema
            validate(instance=request, schema=self._schema)

        except ValueError as e:
            raise ResourceError(f"Invalid search request: {str(e)}")

    def validate_response(self, response: dict[str, Any]) -> None:
        """Validate search response.

        Args:
            response: Search response dictionary

        Raises:
            ResourceError: If response is invalid
        """
        try:
            # Check required fields
            if "results" not in response:
                raise ValueError("Missing results")
            if "total" not in response:
                raise ValueError("Missing total")
            if "query" not in response:
                raise ValueError("Missing query")

            # Validate results
            results = response["results"]
            if not isinstance(results, list):
                raise ValueError("Invalid results")

            for result in results:
                if not isinstance(result, dict):
                    raise ValueError("Invalid result")
                if "id" not in result:
                    raise ValueError("Missing result id")
                if "score" not in result:
                    raise ValueError("Missing result score")
                score = result["score"]
                if not isinstance(score, (int, float)) or score < 0 or score > 1:
                    raise ValueError(f"{score} is greater than the maximum of 1.0")
                if "content" not in result:
                    raise ValueError("Missing content")
                if "metadata" not in result:
                    raise ValueError("Missing metadata")

        except Exception as e:
            raise ResourceError(f"Invalid search response: {str(e)}")

    def search(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute search request.

        Args:
            request: Search request dictionary

        Returns:
            Search response dictionary containing results list

        Raises:
            ResourceError: If search fails
        """
        try:
            # Validate request
            self.validate_request(request)

            # Extract parameters
            parameters = request.get("parameters", {})
            query = parameters["query"]
            n_results = parameters.get("n_results", 10)
            min_score = parameters.get("min_score", 0.0)
            filters = parameters.get("filters")

            # Create query vector
            query_vector = np.random.rand(384).astype(np.float32)  # Mock embedding

            # Query vector store
            results = self._store.query(
                query_vector, n_results=n_results, where=filters
            )

            # Format results
            search_results = []
            for result in results:
                score = 1.0 - result.get(
                    "distance", 0.0
                )  # Convert distance to similarity
                if score >= min_score:
                    search_results.append(
                        {
                            "id": result["id"],
                            "score": score,
                            "content": result["metadata"]["content"],
                            "metadata": result["metadata"],
                        }
                    )

            # Create response dictionary
            response = {
                "results": search_results,
                "total": len(search_results),
                "query": query,
            }

            # Validate response
            self.validate_response(response)
            return response

        except Exception as e:
            raise ResourceError(f"Search failed: {str(e)}")

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
