# Nova Examples

This directory contains example code demonstrating various Nova features and integrations.

## MCP Server Examples

### Echo Server (`mcp/echo_server.py`)
A minimal MCP server that demonstrates basic server setup and tool registration. This server:
- Uses FastAPI for the server implementation
- Provides a simple echo tool
- Shows proper logging configuration
- Demonstrates error handling

### Nova Server (`cli/commands/nova_mcp_server.py`)
The main Nova MCP server implementation that provides Nova's core functionality. This server:
- Exposes Nova's vector search capabilities
- Provides system monitoring tools
- Handles session management
- Implements proper logging and error handling

## Usage

To run any of the example servers:

```bash
# From Nova project root
uv run python -m nova.examples.mcp.echo_server  # For echo server
uv run python -m nova.cli nova_mcp_server       # For Nova server
```

The servers will start and be available at:
- Echo Server: http://127.0.0.1:8766
- Nova Server: http://127.0.0.1:8765

## API Documentation

Once a server is running, you can view its API documentation at:
- Echo Server: http://127.0.0.1:8766/docs
- Nova Server: http://127.0.0.1:8765/docs

The documentation includes:
- Available endpoints
- Request/response models
- Example requests
- Error responses
