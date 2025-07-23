import pytest
from unittest.mock import AsyncMock, patch
from site_crawler.crawler import SiteCrawler
from site_crawler.utils import is_valid_image_url, extract_image_format, clean_text


class TestSiteCrawler:
    @pytest.mark.asyncio
    async def test_crawler_initialization(self):
        crawler = SiteCrawler(max_concurrent=3, timeout=20)
        assert crawler.max_concurrent == 3
        assert crawler.timeout == 20
        assert len(crawler.visited_urls) == 0

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        async with SiteCrawler() as crawler:
            with pytest.raises(ValueError, match="Invalid URL"):
                await crawler.crawl("not-a-url", ["images"])

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_crawl_images_mode(self, mock_get):
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="""
            <html>
                <body>
                    <img src="/product1.jpg" alt="Product 1" class="product-image">
                    <img src="/product2.png" alt="Product 2" class="item-photo">
                    <img src="/logo.png" alt="Logo" class="site-logo">
                </body>
            </html>
        """
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        async with SiteCrawler() as crawler:
            result = await crawler.crawl("https://example.com", ["images"], depth=0)

        assert result["pages_crawled"] == 1
        assert len(result["images"]) >= 2
        assert result["meta"] is None

        # Check image data
        for img in result["images"]:
            assert "url" in img
            assert "alt_text" in img
            assert "format" in img
            assert "page_url" in img

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_crawl_meta_mode(self, mock_get):
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="""
            <html>
                <head>
                    <title>Test Page Title</title>
                    <meta name="description" content="Test description">
                    <meta property="og:title" content="OG Title">
                </head>
                <body>
                    <h1>Main Heading</h1>
                    <h1>Another Heading</h1>
                </body>
            </html>
        """
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        async with SiteCrawler() as crawler:
            result = await crawler.crawl("https://example.com", ["meta"], depth=0)

        assert result["pages_crawled"] == 1
        assert result["images"] is None
        assert len(result["meta"]) == 1

        meta = result["meta"][0]
        assert meta["title"] == "Test Page Title"
        assert meta["description"] == "Test description"
        assert len(meta["h1"]) == 2
        assert meta["og_data"]["title"] == "OG Title"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_crawl_both_modes(self, mock_get):
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="""
            <html>
                <head>
                    <title>Test Page</title>
                </head>
                <body>
                    <img src="/product.jpg" alt="Product">
                </body>
            </html>
        """
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        async with SiteCrawler() as crawler:
            result = await crawler.crawl(
                "https://example.com", ["images", "meta"], depth=0
            )

        assert result["pages_crawled"] == 1
        assert result["images"] is not None
        assert result["meta"] is not None
        assert len(result["images"]) >= 1
        assert len(result["meta"]) == 1


class TestUtils:
    def test_is_valid_image_url(self):
        assert is_valid_image_url("https://example.com/image.jpg")
        assert is_valid_image_url("https://example.com/photo.png")
        assert is_valid_image_url("https://example.com/img/product.webp")
        assert not is_valid_image_url("https://example.com/script.js")
        assert not is_valid_image_url("https://example.com/style.css")
        assert not is_valid_image_url("")

    def test_extract_image_format(self):
        assert extract_image_format("image.jpg") == "jpeg"
        assert extract_image_format("photo.PNG") == "png"
        assert extract_image_format("icon.gif") == "gif"
        assert extract_image_format("unknown.xyz") == "unknown"

    def test_clean_text(self):
        assert clean_text("  Hello   World  ") == "Hello World"
        assert clean_text("Line1\n\n\nLine2") == "Line1 Line2"
        assert clean_text("") == ""
        assert clean_text(None) == ""
