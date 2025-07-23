import re
from urllib.parse import urlparse
from typing import Optional


def get_file_size_str(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def is_valid_image_url(url: str) -> bool:
    """Check if URL points to an image file."""
    if not url:
        return False

    # Check file extension
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".ico",
    }
    parsed = urlparse(url.lower())
    path = parsed.path

    # Remove query parameters
    if "?" in path:
        path = path.split("?")[0]

    for ext in image_extensions:
        if path.endswith(ext):
            return True

    # Check if URL contains image-related patterns
    if re.search(r"/image|/img|/photo|/picture|/media", url, re.I):
        return True

    return False


def extract_image_format(url: str) -> str:
    """Extract image format from URL."""
    url_lower = url.lower()

    formats = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".webp": "webp",
        ".svg": "svg",
        ".bmp": "bmp",
        ".ico": "ico",
    }

    for ext, fmt in formats.items():
        if ext in url_lower:
            return fmt

    return "unknown"


def is_thumbnail_or_icon(
    url: str, width: Optional[int] = None, height: Optional[int] = None
) -> bool:
    """Check if image is likely a thumbnail or icon based on URL and dimensions."""
    url_lower = url.lower()

    # Check URL patterns
    thumbnail_patterns = [
        "thumb",
        "thumbnail",
        "icon",
        "small",
        "tiny",
        "avatar",
        "logo",
        "badge",
        "button",
    ]

    for pattern in thumbnail_patterns:
        if pattern in url_lower:
            return True

    # Check dimensions if available
    if width and height:
        if width < 200 or height < 200:
            return True

    return False


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""

    # Remove extra whitespace
    text = " ".join(text.split())

    # Remove control characters
    text = "".join(char for char in text if char.isprintable())

    return text.strip()


def is_product_image(img_element, url: str) -> bool:
    """Determine if an image is likely a product image."""
    # Check parent elements
    parent = img_element.parent

    if parent:
        parent_classes = " ".join(parent.get("class", []))
        parent_id = parent.get("id", "")

        product_indicators = [
            "product",
            "item",
            "listing",
            "gallery",
            "shop",
            "merchandise",
            "catalog",
        ]

        for indicator in product_indicators:
            if indicator in parent_classes.lower() or indicator in parent_id.lower():
                return True

    # Check image attributes
    img_classes = " ".join(img_element.get("class", []))
    img_id = img_element.get("id", "")
    img_alt = img_element.get("alt", "").lower()

    for indicator in ["product", "item", "shop", "buy", "price", "$"]:
        if (
            indicator in img_classes.lower()
            or indicator in img_id.lower()
            or indicator in img_alt
        ):
            return True

    return False
