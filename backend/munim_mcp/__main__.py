import asyncio
import sys

from munim_mcp.server import serve

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        sys.exit(0)
