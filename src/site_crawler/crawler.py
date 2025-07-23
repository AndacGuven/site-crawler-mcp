"""Enterprise-level site crawler with modular extractor architecture."""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
import validators
from bs4 import BeautifulSoup

from .utils import extract_image_format, get_file_size_str, is_valid_image_url


class CrawlResult:
    """Data container for crawl results with proper encapsulation."""

    def __init__(self, modes: List[str]):
        self.pages_crawled = 0
        self.data = {}

        # Initialize data structure based on modes
        for mode in modes:
            if mode in ["images", "meta", "careers", "references"]:
                self.data[mode] = []
            else:
                self.data[mode] = {}

    def add_page_data(self, page_data: Dict) -> None:
        """Add data from a single page to the result."""
        if not page_data:
            return

        self.pages_crawled += 1

        # Handle list-based data (extend)
        for mode in ["images", "meta", "careers", "references"]:
            if mode in self.data and page_data.get(mode):
                self.data[mode].extend(page_data[mode])

        # Handle dict-based data (update)
        for mode in [
            "brand",
            "seo",
            "performance",
            "security",
            "compliance",
            "infrastructure",
            "legal",
            "contact",
        ]:
            if mode in self.data and page_data.get(mode):
                if self.data[mode]:
                    self.data[mode].update(page_data[mode])
                else:
                    self.data[mode] = page_data[mode]

    def finalize(self) -> Dict:
        """Finalize the result and perform post-processing."""
        result = {
            "pages_crawled": self.pages_crawled,
            **{
                k: v
                if v is not None
                else ([] if k in ["images", "meta", "careers", "references"] else {})
                for k, v in self.data.items()
            },
        }

        # Deduplicate images
        if "images" in result and result["images"]:
            seen = set()
            unique_images = []
            for img in result["images"]:
                if img["url"] not in seen:
                    seen.add(img["url"])
                    unique_images.append(img)
            result["images"] = unique_images

        return result


class BaseExtractor(ABC):
    """Abstract base class for all extractors."""

    @abstractmethod
    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Any:
        """Extract data from the page. Subclasses must implement this method."""
        pass


class ImagesExtractor(BaseExtractor):
    """Extract images from web pages."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> List[Dict]:
        """Extract product images from the page."""
        images = []
        img_elements = []

        # Pattern 1: CSS class patterns
        for pattern in [r"product", r"item", r"shop", r"gallery"]:
            img_elements.extend(soup.find_all("img", class_=re.compile(pattern, re.I)))

        # Pattern 2: Alt text patterns
        img_elements.extend(
            soup.find_all("img", alt=re.compile(r"product|item|shop", re.I))
        )

        # Pattern 3: URL patterns
        img_elements.extend(
            soup.find_all("img", src=re.compile(r"/product|/item|/shop"))
        )

        # Pattern 4: All images in main content areas
        for container in soup.find_all(
            ["main", "article", "section"], class_=re.compile(r"product|content")
        ):
            img_elements.extend(container.find_all("img"))

        # Process found images
        seen_urls = set()
        for img in img_elements:
            img_url = img.get("src", "")
            if not img_url:
                continue

            img_url = urljoin(url, img_url)

            if img_url in seen_urls or not is_valid_image_url(img_url):
                continue
            seen_urls.add(img_url)

            img_data = {
                "url": img_url,
                "alt_text": img.get("alt", ""),
                "format": extract_image_format(img_url),
                "page_url": url,
                "file_size": "Unknown",
            }

            # Get dimensions from attributes
            width, height = img.get("width"), img.get("height")
            if width and height:
                try:
                    img_data["dimensions"] = {
                        "width": int(width),
                        "height": int(height),
                    }
                except ValueError:
                    pass

            images.append(img_data)

        return images


class MetadataExtractor(BaseExtractor):
    """Extract SEO metadata from web pages."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract SEO metadata from the page."""
        meta = {"page_url": url}

        # Extract title
        title_tag = soup.find("title")
        meta["title"] = title_tag.text.strip() if title_tag else ""

        # Extract meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        meta["description"] = desc_tag.get("content", "") if desc_tag else ""

        # Extract H1 tags
        h1_tags = soup.find_all("h1")
        meta["h1"] = [h1.text.strip() for h1 in h1_tags if h1.text.strip()]

        # Extract Open Graph data
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        meta["og_data"] = {
            "title": og_title.get("content", "") if og_title else "",
            "description": og_desc.get("content", "") if og_desc else "",
            "image": og_image.get("content", "") if og_image else "",
        }

        return meta


class BrandExtractor(BaseExtractor):
    """Extract brand and company information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract brand and company information."""
        brand_info = {"page_url": url}

        # Look for logo
        logo_selectors = [
            'img[alt*="logo"]',
            'img[class*="logo"]',
            'img[id*="logo"]',
            ".logo img",
            "#logo img",
            "header img",
        ]

        for selector in logo_selectors:
            logo = soup.select_one(selector)
            if logo and logo.get("src"):
                brand_info["logo_url"] = urljoin(url, logo["src"])
                brand_info["logo_alt"] = logo.get("alt", "")
                break

        # Look for company name in copyright
        company_name_tags = soup.find_all(
            text=re.compile(r"©\s*\d{4}\s*(.+?)(?:\.|,|All)", re.I)
        )
        if company_name_tags:
            match = re.search(
                r"©\s*\d{4}\s*(.+?)(?:\.|,|All)", str(company_name_tags[0]), re.I
            )
            if match:
                brand_info["company_name"] = match.group(1).strip()

        # Look for about us links
        about_links = soup.find_all(
            "a", href=re.compile(r"about|hakkinda|kurumsal", re.I)
        )
        brand_info["about_urls"] = [
            urljoin(url, link["href"]) for link in about_links[:3]
        ]

        # Look for mission/vision statements
        mission_keywords = [
            "mission",
            "vision",
            "misyon",
            "vizyon",
            "değerler",
            "values",
        ]
        for keyword in mission_keywords:
            elements = soup.find_all(text=re.compile(keyword, re.I))
            if elements:
                brand_info[f"{keyword}_found"] = True

        return brand_info


class SEOExtractor(BaseExtractor):
    """Extract comprehensive SEO analysis."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Perform comprehensive SEO analysis."""
        seo = {"page_url": url}

        # Title analysis
        title = soup.find("title")
        title_content = title.text.strip() if title else ""
        seo["title"] = {
            "content": title_content,
            "length": len(title_content),
            "optimal": 30 <= len(title_content) <= 60,
        }

        # Meta description analysis
        desc = soup.find("meta", attrs={"name": "description"})
        desc_content = desc.get("content", "") if desc else ""
        seo["meta_description"] = {
            "content": desc_content,
            "length": len(desc_content),
            "optimal": 120 <= len(desc_content) <= 160,
        }

        # Keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        seo["meta_keywords"] = keywords.get("content", "") if keywords else ""

        # Headings structure
        seo["headings"] = {
            "h1": [h1.text.strip() for h1 in soup.find_all("h1")],
            "h2": [h2.text.strip() for h2 in soup.find_all("h2")[:5]],
            "h3": [h3.text.strip() for h3 in soup.find_all("h3")[:5]],
        }

        # Images analysis
        images = soup.find_all("img")
        images_without_alt = [img for img in images if not img.get("alt")]
        seo["images"] = {
            "total": len(images),
            "without_alt": len(images_without_alt),
            "alt_coverage": f"{((len(images) - len(images_without_alt)) / len(images) * 100):.1f}%"
            if images
            else "N/A",
        }

        # Structured data
        schema_scripts = soup.find_all("script", type="application/ld+json")
        seo["structured_data"] = {
            "found": len(schema_scripts) > 0,
            "count": len(schema_scripts),
        }

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        seo["canonical_url"] = canonical.get("href", "") if canonical else ""

        # Robots meta
        robots = soup.find("meta", attrs={"name": "robots"})
        seo["robots"] = robots.get("content", "") if robots else ""

        # Open Graph
        og_tags = soup.find_all("meta", property=re.compile("^og:"))
        seo["open_graph"] = {
            "found": len(og_tags) > 0,
            "tags": {
                tag.get("property", ""): tag.get("content", "") for tag in og_tags[:10]
            },
        }

        # Twitter Card
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile("^twitter:")})
        seo["twitter_card"] = {
            "found": len(twitter_tags) > 0,
            "tags": {
                tag.get("name", ""): tag.get("content", "") for tag in twitter_tags[:10]
            },
        }

        # Language and mobile
        lang = soup.find("html").get("lang", "") if soup.find("html") else ""
        seo["language"] = lang

        viewport = soup.find("meta", attrs={"name": "viewport"})
        seo["mobile_friendly"] = {
            "viewport_tag": viewport.get("content", "") if viewport else "",
            "has_viewport": viewport is not None,
        }

        return seo


class PerformanceExtractor(BaseExtractor):
    """Extract performance metrics."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract basic performance metrics."""
        session = kwargs.get("session")
        if not session:
            return {"error": "HTTP session required"}

        perf = {"page_url": url}

        try:
            start_time = asyncio.get_event_loop().time()
            async with session.get(url) as response:
                content = await response.read()
                end_time = asyncio.get_event_loop().time()

                perf["load_time"] = f"{(end_time - start_time):.2f}s"
                perf["page_size"] = get_file_size_str(len(content))
                perf["status_code"] = response.status

                # Resource hints
                soup = BeautifulSoup(await response.text(), "lxml")
                perf["resource_hints"] = {
                    "preconnect": len(soup.find_all("link", rel="preconnect")),
                    "prefetch": len(soup.find_all("link", rel="prefetch")),
                    "preload": len(soup.find_all("link", rel="preload")),
                }
        except Exception as e:
            perf["error"] = str(e)

        return perf


class SecurityExtractor(BaseExtractor):
    """Extract security information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract security-related information."""
        response = kwargs.get("response")
        if not response:
            return {"error": "HTTP response required"}

        security = {"page_url": url}

        # Check HTTPS
        parsed_url = urlparse(url)
        security["https"] = parsed_url.scheme == "https"

        # Security headers
        headers = response.headers
        security_headers = {
            "strict-transport-security": "HSTS",
            "x-content-type-options": "X-Content-Type-Options",
            "x-frame-options": "X-Frame-Options",
            "x-xss-protection": "X-XSS-Protection",
            "content-security-policy": "CSP",
            "referrer-policy": "Referrer-Policy",
            "permissions-policy": "Permissions-Policy",
        }

        security["headers"] = {}
        for header, name in security_headers.items():
            value = headers.get(header, "")
            security["headers"][name] = {
                "present": bool(value),
                "value": value[:100] if value else "Not set",
            }

        # SSL/TLS info
        if security["https"]:
            security["ssl"] = {"enabled": True, "url": url}

        return security


class ComplianceExtractor(BaseExtractor):
    """Extract compliance and accessibility information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract compliance and accessibility information."""
        compliance = {"page_url": url}

        # Accessibility metrics
        compliance["accessibility"] = {
            "images_with_alt": len(soup.find_all("img", alt=True)),
            "images_total": len(soup.find_all("img")),
            "forms_with_labels": len(soup.find_all("label")),
            "lang_attribute": bool(soup.find("html", lang=True)),
            "skip_navigation": bool(soup.find(text=re.compile(r"skip.*nav", re.I))),
        }

        # Cookie notice
        cookie_keywords = ["cookie", "çerez", "gdpr", "consent"]
        cookie_elements = []
        for keyword in cookie_keywords:
            cookie_elements.extend(soup.find_all(text=re.compile(keyword, re.I)))
        compliance["cookie_notice"] = len(cookie_elements) > 0

        # ISO certifications
        iso_patterns = [r"ISO\s*\d{4,5}", r"ISO/IEC\s*\d{4,5}"]
        iso_mentions = []
        for pattern in iso_patterns:
            iso_mentions.extend(soup.find_all(text=re.compile(pattern)))

        compliance["iso_certifications"] = list(
            set(
                [
                    re.search(r"ISO[/IEC]*\s*\d{4,5}", str(m)).group()
                    for m in iso_mentions
                    if re.search(r"ISO[/IEC]*\s*\d{4,5}", str(m))
                ]
            )
        )[:5]

        return compliance


class InfrastructureExtractor(BaseExtractor):
    """Extract infrastructure and technology information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract infrastructure and technology information."""
        response = kwargs.get("response")
        if not response:
            return {"error": "HTTP response required"}

        infrastructure = {}

        # Server information
        infrastructure["server"] = response.headers.get("server", "Not disclosed")
        infrastructure["powered_by"] = response.headers.get(
            "x-powered-by", "Not disclosed"
        )

        # CDN detection
        cdn_headers = {
            "cf-ray": "Cloudflare",
            "x-amz-cf-id": "Amazon CloudFront",
            "x-akamai-transformed": "Akamai",
            "x-cdn": "Generic CDN",
        }

        for header, cdn in cdn_headers.items():
            if header in response.headers:
                infrastructure["cdn"] = cdn
                break

        return infrastructure


class LegalExtractor(BaseExtractor):
    """Extract legal and privacy information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract legal and privacy information."""
        legal = {"page_url": url}

        # Privacy policy links
        privacy_links = soup.find_all(
            "a", href=re.compile(r"privacy|gizlilik|kvkk", re.I)
        )
        legal["privacy_policy_urls"] = [
            urljoin(url, link["href"]) for link in privacy_links[:3]
        ]

        # Terms of service
        terms_links = soup.find_all(
            "a", href=re.compile(r"terms|kullanim.*kosul|sozlesme", re.I)
        )
        legal["terms_urls"] = [urljoin(url, link["href"]) for link in terms_links[:3]]

        # KVKK mentions
        kvkk_mentions = soup.find_all(text=re.compile(r"kvkk|kişisel.*veri|6698", re.I))
        legal["kvkk_compliance"] = {
            "mentioned": len(kvkk_mentions) > 0,
            "mention_count": len(kvkk_mentions),
        }

        # Data protection officer
        dpo_patterns = ["veri sorumlusu", "data protection officer", "dpo"]
        dpo_found = any(
            soup.find(text=re.compile(pattern, re.I)) for pattern in dpo_patterns
        )
        legal["data_protection_officer"] = dpo_found

        # Copyright notice
        copyright_text = soup.find(text=re.compile(r"©.*\d{4}", re.I))
        if copyright_text:
            legal["copyright"] = str(copyright_text).strip()[:100]

        return legal


class CareersExtractor(BaseExtractor):
    """Extract career opportunities information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> List[Dict]:
        """Extract career opportunities information."""
        careers = []

        # Find career/job links
        career_links = soup.find_all(
            "a", href=re.compile(r"career|kariyer|job|is.*ilanlari|insan.*kaynak", re.I)
        )

        for link in career_links[:5]:
            career_info = {"text": link.text.strip(), "url": urljoin(url, link["href"])}
            careers.append(career_info)

        # Look for job posting structured data
        job_scripts = soup.find_all("script", type="application/ld+json")
        for script in job_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    careers.append(
                        {
                            "type": "structured_job_posting",
                            "title": data.get("title", ""),
                            "company": data.get("hiringOrganization", {}).get(
                                "name", ""
                            ),
                        }
                    )
            except Exception:
                continue

        return careers


class ReferencesExtractor(BaseExtractor):
    """Extract client references and testimonials."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> List[Dict]:
        """Extract client references and testimonials."""
        references = []

        # Reference keywords
        ref_keywords = [
            "references",
            "referans",
            "clients",
            "müşteri",
            "testimonial",
            "partners",
            "iş ortakları",
        ]

        for keyword in ref_keywords:
            # Find sections with these keywords
            sections = soup.find_all(
                ["section", "div"], class_=re.compile(keyword, re.I)
            )
            sections.extend(
                soup.find_all(["section", "div"], id=re.compile(keyword, re.I))
            )

            for section in sections[:3]:
                # Look for logos or company names
                logos = section.find_all("img")
                for logo in logos[:10]:
                    if logo.get("alt") or logo.get("title"):
                        references.append(
                            {
                                "type": "logo",
                                "name": logo.get("alt") or logo.get("title"),
                                "image_url": urljoin(url, logo.get("src", "")),
                            }
                        )

                # Look for testimonial text
                testimonials = section.find_all(
                    ["blockquote", "p", "div"],
                    class_=re.compile("testimonial|review", re.I),
                )
                for testimonial in testimonials[:5]:
                    if testimonial.text.strip():
                        references.append(
                            {
                                "type": "testimonial",
                                "text": testimonial.text.strip()[:200],
                                "full_text": testimonial.text.strip(),
                            }
                        )

        return references


class ContactExtractor(BaseExtractor):
    """Extract contact information."""

    async def extract(self, soup: BeautifulSoup, url: str, **kwargs) -> Dict:
        """Extract contact information."""
        contact = {"page_url": url}

        # Email addresses
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = set()
        for text in soup.stripped_strings:
            found_emails = re.findall(email_pattern, text)
            emails.update(found_emails)
        contact["emails"] = list(emails)[:5]

        # Phone numbers
        phone_patterns = [
            r"\+90[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}",
            r"0\d{3}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}",
            r"\(\d{3}\)[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}",
            r"\+\d{1,3}[\s.-]?\d{3,14}",
        ]
        phones = set()
        for pattern in phone_patterns:
            for text in soup.stripped_strings:
                found_phones = re.findall(pattern, text)
                phones.update(found_phones)
        contact["phones"] = list(phones)[:5]

        # Social media links
        social_patterns = {
            "facebook": r"facebook\.com/[\w.-]+",
            "twitter": r"twitter\.com/[\w.-]+",
            "linkedin": r"linkedin\.com/(?:company|in)/[\w.-]+",
            "instagram": r"instagram\.com/[\w.-]+",
            "youtube": r"youtube\.com/(?:c|channel|user)/[\w.-]+",
        }

        contact["social_media"] = {}
        for platform, pattern in social_patterns.items():
            links = soup.find_all("a", href=re.compile(pattern, re.I))
            if links:
                contact["social_media"][platform] = links[0]["href"]

        # Address
        address_keywords = ["adres", "address", "konum", "location"]
        for keyword in address_keywords:
            address_elements = soup.find_all(text=re.compile(keyword, re.I))
            for elem in address_elements:
                parent = elem.parent
                if parent:
                    address_text = parent.get_text(strip=True)
                    if 20 < len(address_text) < 300:
                        contact["address"] = address_text
                        break
            if contact.get("address"):
                break

        # Contact page links
        contact_links = soup.find_all(
            "a", href=re.compile(r"contact|iletisim|bize.*ulas", re.I)
        )
        contact["contact_page_urls"] = [
            urljoin(url, link["href"]) for link in contact_links[:3]
        ]

        return contact


class ExtractorRegistry:
    """Factory for managing all extractors."""

    def __init__(self):
        self._extractors = {
            "images": ImagesExtractor(),
            "meta": MetadataExtractor(),
            "brand": BrandExtractor(),
            "seo": SEOExtractor(),
            "performance": PerformanceExtractor(),
            "security": SecurityExtractor(),
            "compliance": ComplianceExtractor(),
            "infrastructure": InfrastructureExtractor(),
            "legal": LegalExtractor(),
            "careers": CareersExtractor(),
            "references": ReferencesExtractor(),
            "contact": ContactExtractor(),
        }

    def get_extractor(self, mode: str) -> Optional[BaseExtractor]:
        """Get extractor for a specific mode."""
        return self._extractors.get(mode)

    def get_extractors_for_modes(self, modes: List[str]) -> Dict[str, BaseExtractor]:
        """Get extractors for multiple modes."""
        return {
            mode: self._extractors[mode] for mode in modes if mode in self._extractors
        }


class SiteCrawler:
    """Main crawler orchestrator with enterprise architecture."""

    def __init__(self, max_concurrent: int = 5, timeout: int = 30):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.visited_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.extractor_registry = ExtractorRegistry()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "Mozilla/5.0 (compatible; SiteCrawlerMCP/1.0)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            await asyncio.sleep(0.1)

    async def crawl(
        self, url: str, modes: List[str], depth: int = 1, max_pages: int = 50
    ) -> Dict:
        """Main crawl method using enterprise architecture."""
        if not validators.url(url):
            raise ValueError(f"Invalid URL: {url}")

        result = CrawlResult(modes)
        await self._crawl_recursive(url, modes, depth, max_pages, result, 0)
        return result.finalize()

    async def _crawl_recursive(
        self,
        url: str,
        modes: List[str],
        max_depth: int,
        max_pages: int,
        result: CrawlResult,
        current_depth: int,
    ):
        """Recursively crawl pages using the new architecture."""
        if (
            current_depth > max_depth
            or url in self.visited_urls
            or result.pages_crawled >= max_pages
        ):
            return

        self.visited_urls.add(url)

        async with self.semaphore:
            try:
                page_data = await self._crawl_page(url, modes)
                if page_data:
                    result.add_page_data(page_data)

                    # Continue crawling if depth allows
                    if current_depth < max_depth:
                        tasks = []
                        for link in page_data.get("links", [])[:10]:
                            if link not in self.visited_urls:
                                task = self._crawl_recursive(
                                    link,
                                    modes,
                                    max_depth,
                                    max_pages,
                                    result,
                                    current_depth + 1,
                                )
                                tasks.append(task)

                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"Error crawling {url}: {str(e)}")

    async def _crawl_page(self, url: str, modes: List[str]) -> Optional[Dict]:
        """Crawl a single page using extractors."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")
                result = {"url": url}

                # Get extractors for requested modes
                extractors = self.extractor_registry.get_extractors_for_modes(modes)

                # Execute extractors
                for mode, extractor in extractors.items():
                    try:
                        kwargs = {}
                        if mode in ["performance"]:
                            kwargs["session"] = self.session
                        if mode in ["security", "infrastructure"]:
                            kwargs["response"] = response

                        extracted_data = await extractor.extract(soup, url, **kwargs)
                        if extracted_data:
                            result[mode] = extracted_data
                    except Exception as e:
                        print(f"Error in {mode} extractor for {url}: {str(e)}")

                # Extract links for crawling
                result["links"] = self._extract_links(soup, url)
                return result

        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links for crawling."""
        links = []
        base_domain = urlparse(base_url).netloc

        for link in soup.find_all("a", href=True):
            href = link["href"]
            absolute_url = urljoin(base_url, href)

            if urlparse(absolute_url).netloc == base_domain:
                links.append(absolute_url)

        return list(set(links))  # Remove duplicates
