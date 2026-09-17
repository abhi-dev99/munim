import logging
import asyncio
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolRequest, CallToolResult

from munim_mcp.tools import get_tools_list, call_tool_handler

logger = logging.getLogger(__name__)

app = Server("munim-ai")

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for Munim AI."""
    return get_tools_list()

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Handle tool execution."""
    args = arguments or {}
    try:
        result = await call_tool_handler(name, args)
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]

async def serve():
    """Run the MCP server over stdio."""
    logger.info("Starting Munim AI MCP Server over stdio")
    # Initialize necessary backend components here if needed
    from app.config import get_settings
    settings = get_settings()
    
    options = app.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            options,
        )
