# Site Crawler MCP

A powerful Model Context Protocol (MCP) server for crawling websites and extracting assets including images and SEO metadata. Built for e-commerce sites and general web crawling needs.

## Features

- **Comprehensive website analysis**: 12 different extraction modes for complete website insights
- **Multi-mode crawling**: Extract multiple data types in a single pass
- **Smart extraction**: Advanced pattern matching for accurate data extraction
- **Performance optimized**: Concurrent crawling with rate limiting
- **Security analysis**: HTTPS, security headers, SSL/TLS information
- **SEO analysis**: Complete SEO audit including meta tags, structured data, and more
- **Legal compliance**: KVKK, GDPR, privacy policy detection
- **Business intelligence**: Brand info, references, contact details extraction

## Installation

### From PyPI (when published)
```bash
pip install site-crawler-mcp
```

### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/AndacGuven/site-crawler-mcp.git
cd site-crawler-mcp

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Usage

### As an MCP Server

Add to your MCP configuration file (usually located at `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "site-crawler": {
      "command": "python",
      "args": ["-m", "site_crawler.server"],
      "cwd": "C:\\path\\to\\site-crawler-mcp\\src",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\site-crawler-mcp\\src"
      }
    }
  }
}
```

**Note**: Replace `C:\\path\\to\\site-crawler-mcp` with your actual project path.

### Available Tools

#### `site_crawlAssets`

Crawl a website and extract various assets based on specified modes.

**Parameters:**
- `url` (string, required): The URL to start crawling from
- `modes` (array, required): Array of extraction modes (see below)
- `depth` (number, optional): Crawling depth (default: 1)
- `max_pages` (number, optional): Maximum pages to crawl (default: 50)

**Available Modes:**
- `images`: Extract all images with metadata (alt text, dimensions, format)
- `meta`: Basic SEO metadata (title, description, H1 tags)
- `brand`: Company branding information (logo, name, about pages)
- `seo`: Comprehensive SEO analysis (meta tags, structured data, open graph)
- `performance`: Page load metrics and performance indicators
- `security`: Security headers and HTTPS configuration
- `compliance`: Accessibility and regulatory compliance checks
- `infrastructure`: Server technology and CDN detection
- `legal`: Privacy policies, terms, KVKK compliance
- `careers`: Job opportunities and career pages
- `references`: Client testimonials and case studies
- `contact`: Contact information (email, phone, social media, address)

**Example Requests:**

1. Basic image extraction:
```json
{
  "tool": "site_crawlAssets",
  "arguments": {
    "url": "https://example.com",
    "modes": ["images"],
    "depth": 1
  }
}
```

2. Full SEO and security audit:
```json
{
  "tool": "site_crawlAssets",
  "arguments": {
    "url": "https://example.com",
    "modes": ["seo", "security", "performance"],
    "depth": 2
  }
}
```

3. Business intelligence gathering:
```json
{
  "tool": "site_crawlAssets",
  "arguments": {
    "url": "https://example.com",
    "modes": ["brand", "contact", "references", "careers"],
    "depth": 3
  }
}
```

4. Legal compliance check:
```json
{
  "tool": "site_crawlAssets",
  "arguments": {
    "url": "https://example.com",
    "modes": ["legal", "compliance"],
    "depth": 2
  }
}
```

## Development

### Requirements

- Python 3.8+
- BeautifulSoup4
- aiohttp
- MCP SDK

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/AndacGuven/site-crawler-mcp.git
cd site-crawler-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
site-crawler-mcp/
├── README.md
├── requirements.txt
├── setup.py
├── src/
│   └── site_crawler/
│       ├── __init__.py
│       ├── server.py
│       ├── crawler.py
│       └── utils.py
└── tests/
    ├── __init__.py
    └── test_crawler.py
```

## Configuration

### Environment Variables

- `CRAWLER_MAX_CONCURRENT`: Maximum concurrent requests (default: 5)
- `CRAWLER_TIMEOUT`: Request timeout in seconds (default: 30)
- `CRAWLER_USER_AGENT`: Custom user agent string

### Rate Limiting

The crawler respects `robots.txt` and implements polite crawling:
- 1-2 second delay between requests to the same domain
- Maximum 5 concurrent requests
- Automatic retry with exponential backoff

## Use Cases

### E-commerce Analysis
Extract product images, pricing, and brand information:
```
"Analyze the e-commerce site example.com for product images, brand info, and contact details"
```

### SEO and Performance Audit
Comprehensive SEO and performance analysis:
```
"Perform a full SEO audit of example.com including performance metrics and structured data"
```

### Security Assessment
Check security headers and HTTPS configuration:
```
"Analyze the security posture of example.com including headers and SSL configuration"
```

### Legal Compliance Check
Verify KVKK/GDPR compliance and privacy policies:
```
"Check example.com for KVKK compliance, privacy policies, and data protection measures"
```

### Business Intelligence
Gather company information and references:
```
"Extract business information from example.com including company details, references, and career opportunities"
```

### Contact Information Extraction
Find all contact details:
```
"Find all contact information on example.com including emails, phones, social media, and addresses"
```

## Performance Considerations

- Images smaller than 50KB are filtered out by default
- Concurrent crawling limited to 5 pages simultaneously
- Memory-efficient streaming for large sites
- Automatic deduplication of URLs

## Error Handling

The crawler handles various error scenarios gracefully:
- Network timeouts
- Invalid URLs
- Rate limiting (429 responses)
- JavaScript-heavy sites (graceful degradation)
- Memory limits

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [MCP SDK](https://github.com/modelcontextprotocol/sdk)
- Inspired by the need for better e-commerce crawling tools
- Thanks to the open-source community

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/AndacGuven/site-crawler-mcp/issues).