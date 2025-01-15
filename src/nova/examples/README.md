# Nova Examples

This directory contains example implementations and demonstrations of Nova's features.

## MCP Examples

### Echo Server
Location: `mcp/echo_server.py`

A minimal FastMCP server that demonstrates Claude Desktop integration. This server:
- Uses FastMCP's high-level features
- Shows proper tool registration
- Implements structured logging
- Handles errors gracefully

#### Setup and Configuration

##### 1. Shell Script
The server is started via `scripts/start_echo.sh`, which:
- Sets up the Python environment correctly
- Configures PYTHONPATH
- Ensures proper working directory
- Runs the server with uv

##### 2. Claude Desktop Configuration
Edit your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "echo": {
      "command": "/Users/chadwalters/source/nova/scripts/start_echo.sh",
      "cwd": "/Users/chadwalters/source/nova"
    }
  }
}
```

#### Verifying Setup
1. Start a new conversation in Claude Desktop
2. The "echo" tool should appear in Claude's capabilities
3. Try using it with: "Use the echo tool to send 'hello world'"
4. Check logs at `.nova/logs/mcp_echo.log` for server activity

#### Troubleshooting
- If tool doesn't appear:
  - Verify server is running (`ps aux | grep echo_server`)
  - Check logs for startup errors
  - Restart Claude Desktop
- If connection fails:
  - Check if start_echo.sh is executable (`chmod +x scripts/start_echo.sh`)
  - Verify paths in start_echo.sh are correct
  - Look for connection errors in Claude Desktop developer console
