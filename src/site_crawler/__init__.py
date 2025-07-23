"""Site Crawler MCP - Extract images and metadata from websites."""

__version__ = "0.1.0"
__author__ = "Your Name"

from .crawler import SiteCrawler
from .main import main
from .server import SiteCrawlerServer

__all__ = ["SiteCrawler", "SiteCrawlerServer", "main"]
