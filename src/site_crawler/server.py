import asyncio
import json
import logging
from typing import Any, Dict
import mcp.server.stdio
import mcp.types as types
from .crawler import SiteCrawler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SiteCrawlerServer:
    def __init__(self):
        self.server = mcp.server.Server("site-crawler-mcp")
        self.setup_handlers()
        
    def setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="site_crawlAssets",
                    description="Extract images and metadata from websites",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "format": "uri",
                                "description": "Website URL to crawl"
                            },
                            "modes": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["images", "meta", "brand", "seo", "performance", "security", "compliance", "infrastructure", "legal", "careers", "references", "contact"]
                                },
                                "description": "Extraction modes: images, meta, brand, seo, performance, security, compliance, infrastructure, legal, careers, references, contact",
                                "minItems": 1
                            },
                            "depth": {
                                "type": "number",
                                "default": 1,
                                "minimum": 0,
                                "maximum": 5,
                                "description": "Crawling depth (default: 1)"
                            },
                            "max_pages": {
                                "type": "number",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 500,
                                "description": "Maximum pages to crawl"
                            }
                        },
                        "required": ["url", "modes"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            if name == "site_crawlAssets":
                return await self.crawl_assets(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
                
    async def crawl_assets(self, arguments: Dict[str, Any]) -> list[types.TextContent]:
        """Handle the site.crawlAssets tool call."""
        url = arguments.get("url")
        modes = arguments.get("modes", ["images"])
        depth = arguments.get("depth", 1)
        max_pages = arguments.get("max_pages", 50)
        
        if not url:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "URL is required"})
            )]
            
        if not modes:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "At least one mode is required"})
            )]
            
        try:
            async with SiteCrawler() as crawler:
                result = await crawler.crawl(url, modes, depth, max_pages)
                
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Crawling failed: {str(e)}",
                    "url": url
                })
            )]
            
    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                mcp.server.InitializationOptions(
                    server_name="site-crawler-mcp",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=mcp.server.NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def main():
    """Main entry point for the MCP server."""
    server = SiteCrawlerServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()