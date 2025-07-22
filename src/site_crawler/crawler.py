import asyncio
import json
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
import validators
from .utils import get_file_size_str, is_valid_image_url, extract_image_format


class SiteCrawler:
    def __init__(self, max_concurrent: int = 5, timeout: int = 30):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.visited_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; SiteCrawlerMCP/1.0)'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def crawl(self, url: str, modes: List[str], depth: int = 1, max_pages: int = 50) -> Dict:
        """
        Crawl a website and extract assets based on modes.
        
        Args:
            url: Starting URL
            modes: List of extraction modes ["images", "meta"]
            depth: Maximum crawling depth
            max_pages: Maximum pages to crawl
            
        Returns:
            Dictionary with crawled data
        """
        if not validators.url(url):
            raise ValueError(f"Invalid URL: {url}")
            
        result = {
            "pages_crawled": 0,
            "images": [] if "images" in modes else None,
            "meta": [] if "meta" in modes else None,
            "brand": {} if "brand" in modes else None,
            "seo": {} if "seo" in modes else None,
            "performance": {} if "performance" in modes else None,
            "security": {} if "security" in modes else None,
            "compliance": {} if "compliance" in modes else None,
            "infrastructure": {} if "infrastructure" in modes else None,
            "legal": {} if "legal" in modes else None,
            "careers": [] if "careers" in modes else None,
            "references": [] if "references" in modes else None,
            "contact": {} if "contact" in modes else None
        }
        
        # Start crawling from the given URL
        await self._crawl_recursive(url, modes, depth, max_pages, result, current_depth=0)
        
        # Deduplicate images
        if result["images"] is not None:
            seen = set()
            unique_images = []
            for img in result["images"]:
                if img["url"] not in seen:
                    seen.add(img["url"])
                    unique_images.append(img)
            result["images"] = unique_images
            
        return result
        
    async def _crawl_recursive(self, url: str, modes: List[str], max_depth: int, 
                              max_pages: int, result: Dict, current_depth: int):
        """Recursively crawl pages up to max_depth."""
        if current_depth > max_depth:
            return
            
        if url in self.visited_urls:
            return
            
        if result["pages_crawled"] >= max_pages:
            return
            
        self.visited_urls.add(url)
        
        async with self.semaphore:
            try:
                page_data = await self._crawl_page(url, modes)
                if page_data:
                    result["pages_crawled"] += 1
                    
                    if "images" in modes and page_data.get("images"):
                        result["images"].extend(page_data["images"])
                        
                    if "meta" in modes and page_data.get("meta"):
                        result["meta"].append(page_data["meta"])
                    
                    # Merge single-value results
                    for mode in ["brand", "seo", "performance", "security", "compliance", 
                                "infrastructure", "legal", "contact"]:
                        if mode in modes and page_data.get(mode):
                            if result[mode]:
                                result[mode].update(page_data[mode])
                            else:
                                result[mode] = page_data[mode]
                    
                    # Extend list-based results
                    if "careers" in modes and page_data.get("careers"):
                        result["careers"].extend(page_data["careers"])
                    
                    if "references" in modes and page_data.get("references"):
                        result["references"].extend(page_data["references"])
                        
                    # Crawl linked pages if depth allows
                    if current_depth < max_depth:
                        tasks = []
                        for link in page_data.get("links", [])[:10]:  # Limit links per page
                            if link not in self.visited_urls:
                                task = self._crawl_recursive(
                                    link, modes, max_depth, max_pages, result, current_depth + 1
                                )
                                tasks.append(task)
                                
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                            
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error crawling {url}: {str(e)}")
                
    async def _crawl_page(self, url: str, modes: List[str]) -> Optional[Dict]:
        """Crawl a single page and extract requested data."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                result = {"url": url}
                
                # Extract images if requested
                if "images" in modes:
                    result["images"] = await self._extract_images(soup, url)
                    
                # Extract metadata if requested
                if "meta" in modes:
                    result["meta"] = self._extract_metadata(soup, url)
                
                # Extract brand information
                if "brand" in modes:
                    result["brand"] = self._extract_brand_info(soup, url)
                
                # Extract SEO analysis
                if "seo" in modes:
                    result["seo"] = self._extract_seo_analysis(soup, url, html)
                
                # Extract performance metrics
                if "performance" in modes:
                    result["performance"] = await self._extract_performance_metrics(url)
                
                # Extract security information
                if "security" in modes:
                    result["security"] = await self._extract_security_info(url, response)
                
                # Extract compliance information
                if "compliance" in modes:
                    result["compliance"] = self._extract_compliance_info(soup, url)
                
                # Extract infrastructure information
                if "infrastructure" in modes:
                    result["infrastructure"] = await self._extract_infrastructure_info(response)
                
                # Extract legal information
                if "legal" in modes:
                    result["legal"] = self._extract_legal_info(soup, url)
                
                # Extract career opportunities
                if "careers" in modes:
                    result["careers"] = self._extract_careers_info(soup, url)
                
                # Extract references
                if "references" in modes:
                    result["references"] = self._extract_references(soup, url)
                
                # Extract contact information
                if "contact" in modes:
                    result["contact"] = self._extract_contact_info(soup, url)
                    
                # Extract links for recursive crawling
                result["links"] = self._extract_links(soup, url)
                
                return result
                
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
            
    async def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract product images from the page."""
        images = []
        
        # Multiple patterns to find product images
        img_elements = []
        
        # Pattern 1: CSS class patterns
        for pattern in [r'product', r'item', r'shop', r'gallery']:
            img_elements.extend(soup.find_all('img', class_=re.compile(pattern, re.I)))
            
        # Pattern 2: Alt text patterns
        img_elements.extend(soup.find_all('img', alt=re.compile(r'product|item|shop', re.I)))
        
        # Pattern 3: URL patterns
        img_elements.extend(soup.find_all('img', src=re.compile(r'/product|/item|/shop')))
        
        # Pattern 4: All images in main content areas
        for container in soup.find_all(['main', 'article', 'section'], class_=re.compile(r'product|content')):
            img_elements.extend(container.find_all('img'))
            
        # Process found images
        seen_urls = set()
        for img in img_elements:
            img_url = img.get('src', '')
            if not img_url:
                continue
                
            # Make URL absolute
            img_url = urljoin(base_url, img_url)
            
            # Skip if already processed
            if img_url in seen_urls:
                continue
            seen_urls.add(img_url)
            
            # Skip if not a valid image URL
            if not is_valid_image_url(img_url):
                continue
                
            # Extract image data
            img_data = {
                "url": img_url,
                "alt_text": img.get('alt', ''),
                "format": extract_image_format(img_url),
                "page_url": base_url
            }
            
            # Try to get dimensions from attributes
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    img_data["dimensions"] = {
                        "width": int(width),
                        "height": int(height)
                    }
                except ValueError:
                    pass
                    
            # Estimate file size if possible
            img_data["file_size"] = "Unknown"
            
            images.append(img_data)
            
        return images
        
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract SEO metadata from the page."""
        meta = {"page_url": url}
        
        # Extract title
        title_tag = soup.find('title')
        meta["title"] = title_tag.text.strip() if title_tag else ""
        
        # Extract meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        meta["description"] = desc_tag.get('content', '') if desc_tag else ""
        
        # Extract H1 tags
        h1_tags = soup.find_all('h1')
        meta["h1"] = [h1.text.strip() for h1 in h1_tags if h1.text.strip()]
        
        # Extract Open Graph data
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        
        meta["og_data"] = {
            "title": og_title.get('content', '') if og_title else "",
            "description": og_desc.get('content', '') if og_desc else "",
            "image": og_image.get('content', '') if og_image else ""
        }
        
        return meta
        
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links for crawling."""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Only include internal links
            if urlparse(absolute_url).netloc == base_domain:
                links.append(absolute_url)
                
        return list(set(links))  # Remove duplicates
    
    def _extract_brand_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract brand and company information."""
        brand_info = {"page_url": url}
        
        # Look for logo
        logo_selectors = ['img[alt*="logo"]', 'img[class*="logo"]', 'img[id*="logo"]', 
                         '.logo img', '#logo img', 'header img']
        for selector in logo_selectors:
            logo = soup.select_one(selector)
            if logo and logo.get('src'):
                brand_info["logo_url"] = urljoin(url, logo['src'])
                brand_info["logo_alt"] = logo.get('alt', '')
                break
        
        # Look for company name in various places
        company_name_tags = soup.find_all(text=re.compile(r'©\s*\d{4}\s*(.+?)(?:\.|,|All)', re.I))
        if company_name_tags:
            match = re.search(r'©\s*\d{4}\s*(.+?)(?:\.|,|All)', str(company_name_tags[0]), re.I)
            if match:
                brand_info["company_name"] = match.group(1).strip()
        
        # Look for about us link
        about_links = soup.find_all('a', href=re.compile(r'about|hakkinda|kurumsal', re.I))
        brand_info["about_urls"] = [urljoin(url, link['href']) for link in about_links[:3]]
        
        # Look for mission/vision statements
        mission_keywords = ['mission', 'vision', 'misyon', 'vizyon', 'değerler', 'values']
        for keyword in mission_keywords:
            elements = soup.find_all(text=re.compile(keyword, re.I))
            if elements:
                brand_info[f"{keyword}_found"] = True
        
        return brand_info
    
    def _extract_seo_analysis(self, soup: BeautifulSoup, url: str, html: str) -> Dict:
        """Perform comprehensive SEO analysis."""
        seo = {"page_url": url}
        
        # Basic meta tags
        title = soup.find('title')
        seo["title"] = {
            "content": title.text.strip() if title else "",
            "length": len(title.text.strip()) if title else 0,
            "optimal": 30 <= len(title.text.strip()) <= 60 if title else False
        }
        
        # Meta description
        desc = soup.find('meta', attrs={'name': 'description'})
        desc_content = desc.get('content', '') if desc else ""
        seo["meta_description"] = {
            "content": desc_content,
            "length": len(desc_content),
            "optimal": 120 <= len(desc_content) <= 160
        }
        
        # Keywords
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        seo["meta_keywords"] = keywords.get('content', '') if keywords else ""
        
        # Headings structure
        seo["headings"] = {
            "h1": [h1.text.strip() for h1 in soup.find_all('h1')],
            "h2": [h2.text.strip() for h2 in soup.find_all('h2')[:5]],
            "h3": [h3.text.strip() for h3 in soup.find_all('h3')[:5]]
        }
        
        # Images without alt text
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        seo["images"] = {
            "total": len(images),
            "without_alt": len(images_without_alt),
            "alt_coverage": f"{((len(images) - len(images_without_alt)) / len(images) * 100):.1f}%" if images else "N/A"
        }
        
        # Schema.org structured data
        schema_scripts = soup.find_all('script', type='application/ld+json')
        seo["structured_data"] = {
            "found": len(schema_scripts) > 0,
            "count": len(schema_scripts)
        }
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        seo["canonical_url"] = canonical.get('href', '') if canonical else ""
        
        # Robots meta
        robots = soup.find('meta', attrs={'name': 'robots'})
        seo["robots"] = robots.get('content', '') if robots else ""
        
        # Open Graph
        og_tags = soup.find_all('meta', property=re.compile('^og:'))
        seo["open_graph"] = {
            "found": len(og_tags) > 0,
            "tags": {tag.get('property', ''): tag.get('content', '') for tag in og_tags[:10]}
        }
        
        # Twitter Card
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile('^twitter:')})
        seo["twitter_card"] = {
            "found": len(twitter_tags) > 0,
            "tags": {tag.get('name', ''): tag.get('content', '') for tag in twitter_tags[:10]}
        }
        
        # Language
        lang = soup.find('html').get('lang', '') if soup.find('html') else ''
        seo["language"] = lang
        
        # Mobile viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        seo["mobile_friendly"] = {
            "viewport_tag": viewport.get('content', '') if viewport else "",
            "has_viewport": viewport is not None
        }
        
        return seo
    
    async def _extract_performance_metrics(self, url: str) -> Dict:
        """Extract basic performance metrics."""
        perf = {"page_url": url}
        
        try:
            start_time = asyncio.get_event_loop().time()
            async with self.session.get(url) as response:
                content = await response.read()
                end_time = asyncio.get_event_loop().time()
                
                perf["load_time"] = f"{(end_time - start_time):.2f}s"
                perf["page_size"] = get_file_size_str(len(content))
                perf["status_code"] = response.status
                
                # Resource hints
                soup = BeautifulSoup(await response.text(), 'lxml')
                perf["resource_hints"] = {
                    "preconnect": len(soup.find_all('link', rel='preconnect')),
                    "prefetch": len(soup.find_all('link', rel='prefetch')),
                    "preload": len(soup.find_all('link', rel='preload'))
                }
                
        except Exception as e:
            perf["error"] = str(e)
            
        return perf
    
    async def _extract_security_info(self, url: str, response) -> Dict:
        """Extract security-related information."""
        security = {"page_url": url}
        
        # Check HTTPS
        parsed_url = urlparse(url)
        security["https"] = parsed_url.scheme == 'https'
        
        # Security headers
        headers = response.headers
        security_headers = {
            'strict-transport-security': 'HSTS',
            'x-content-type-options': 'X-Content-Type-Options',
            'x-frame-options': 'X-Frame-Options',
            'x-xss-protection': 'X-XSS-Protection',
            'content-security-policy': 'CSP',
            'referrer-policy': 'Referrer-Policy',
            'permissions-policy': 'Permissions-Policy'
        }
        
        security["headers"] = {}
        for header, name in security_headers.items():
            value = headers.get(header, '')
            security["headers"][name] = {
                "present": bool(value),
                "value": value[:100] if value else "Not set"
            }
        
        # SSL/TLS info (basic check)
        if security["https"]:
            security["ssl"] = {
                "enabled": True,
                "url": url
            }
        
        return security
    
    def _extract_compliance_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract compliance and accessibility information."""
        compliance = {"page_url": url}
        
        # Accessibility
        compliance["accessibility"] = {
            "images_with_alt": len(soup.find_all('img', alt=True)),
            "images_total": len(soup.find_all('img')),
            "forms_with_labels": len(soup.find_all('label')),
            "lang_attribute": bool(soup.find('html', lang=True)),
            "skip_navigation": bool(soup.find(text=re.compile(r'skip.*nav', re.I)))
        }
        
        # Cookie notice
        cookie_keywords = ['cookie', 'çerez', 'gdpr', 'consent']
        cookie_elements = []
        for keyword in cookie_keywords:
            cookie_elements.extend(soup.find_all(text=re.compile(keyword, re.I)))
        compliance["cookie_notice"] = len(cookie_elements) > 0
        
        # ISO certifications
        iso_patterns = [r'ISO\s*\d{4,5}', r'ISO/IEC\s*\d{4,5}']
        iso_mentions = []
        for pattern in iso_patterns:
            iso_mentions.extend(soup.find_all(text=re.compile(pattern)))
        compliance["iso_certifications"] = list(set([re.search(r'ISO[/IEC]*\s*\d{4,5}', str(m)).group() for m in iso_mentions if re.search(r'ISO[/IEC]*\s*\d{4,5}', str(m))]))[:5]
        
        return compliance
    
    async def _extract_infrastructure_info(self, response) -> Dict:
        """Extract infrastructure and technology information."""
        infrastructure = {}
        
        # Server header
        infrastructure["server"] = response.headers.get('server', 'Not disclosed')
        
        # Powered by
        infrastructure["powered_by"] = response.headers.get('x-powered-by', 'Not disclosed')
        
        # CDN detection
        cdn_headers = {
            'cf-ray': 'Cloudflare',
            'x-amz-cf-id': 'Amazon CloudFront',
            'x-akamai-transformed': 'Akamai',
            'x-cdn': 'Generic CDN'
        }
        
        for header, cdn in cdn_headers.items():
            if header in response.headers:
                infrastructure["cdn"] = cdn
                break
        
        return infrastructure
    
    def _extract_legal_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract legal and privacy information."""
        legal = {"page_url": url}
        
        # Privacy policy links
        privacy_links = soup.find_all('a', href=re.compile(r'privacy|gizlilik|kvkk', re.I))
        legal["privacy_policy_urls"] = [urljoin(url, link['href']) for link in privacy_links[:3]]
        
        # Terms of service
        terms_links = soup.find_all('a', href=re.compile(r'terms|kullanim.*kosul|sozlesme', re.I))
        legal["terms_urls"] = [urljoin(url, link['href']) for link in terms_links[:3]]
        
        # KVKK mentions
        kvkk_mentions = soup.find_all(text=re.compile(r'kvkk|kişisel.*veri|6698', re.I))
        legal["kvkk_compliance"] = {
            "mentioned": len(kvkk_mentions) > 0,
            "mention_count": len(kvkk_mentions)
        }
        
        # Data protection officer
        dpo_patterns = ['veri sorumlusu', 'data protection officer', 'dpo']
        dpo_found = False
        for pattern in dpo_patterns:
            if soup.find(text=re.compile(pattern, re.I)):
                dpo_found = True
                break
        legal["data_protection_officer"] = dpo_found
        
        # Copyright notice
        copyright_text = soup.find(text=re.compile(r'©.*\d{4}', re.I))
        if copyright_text:
            legal["copyright"] = str(copyright_text).strip()[:100]
        
        return legal
    
    def _extract_careers_info(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract career opportunities information."""
        careers = []
        
        # Find career/job links
        career_links = soup.find_all('a', href=re.compile(r'career|kariyer|job|is.*ilanlari|insan.*kaynak', re.I))
        
        for link in career_links[:5]:
            career_info = {
                "text": link.text.strip(),
                "url": urljoin(url, link['href'])
            }
            careers.append(career_info)
        
        # Look for job posting structured data
        job_scripts = soup.find_all('script', type='application/ld+json')
        for script in job_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    careers.append({
                        "type": "structured_job_posting",
                        "title": data.get('title', ''),
                        "company": data.get('hiringOrganization', {}).get('name', '')
                    })
            except:
                pass
        
        return careers
    
    def _extract_references(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract client references and testimonials."""
        references = []
        
        # Look for reference/client sections
        ref_keywords = ['references', 'referans', 'clients', 'müşteri', 'testimonial', 'partners', 'iş ortakları']
        
        for keyword in ref_keywords:
            # Find sections with these keywords
            sections = soup.find_all(['section', 'div'], class_=re.compile(keyword, re.I))
            sections.extend(soup.find_all(['section', 'div'], id=re.compile(keyword, re.I)))
            
            for section in sections[:3]:
                # Look for logos or company names
                logos = section.find_all('img')
                for logo in logos[:10]:
                    if logo.get('alt') or logo.get('title'):
                        references.append({
                            "type": "logo",
                            "name": logo.get('alt') or logo.get('title'),
                            "image_url": urljoin(url, logo.get('src', ''))
                        })
                
                # Look for testimonial text
                testimonials = section.find_all(['blockquote', 'p', 'div'], class_=re.compile('testimonial|review', re.I))
                for testimonial in testimonials[:5]:
                    if testimonial.text.strip():
                        references.append({
                            "type": "testimonial",
                            "text": testimonial.text.strip()[:200],
                            "full_text": testimonial.text.strip()
                        })
        
        return references
    
    def _extract_contact_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract contact information."""
        contact = {"page_url": url}
        
        # Email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = set()
        for text in soup.stripped_strings:
            found_emails = re.findall(email_pattern, text)
            emails.update(found_emails)
        contact["emails"] = list(emails)[:5]
        
        # Phone numbers (Turkish and international formats)
        phone_patterns = [
            r'\+90[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}',
            r'0\d{3}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}',
            r'\(\d{3}\)[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}',
            r'\+\d{1,3}[\s.-]?\d{3,14}'
        ]
        phones = set()
        for pattern in phone_patterns:
            for text in soup.stripped_strings:
                found_phones = re.findall(pattern, text)
                phones.update(found_phones)
        contact["phones"] = list(phones)[:5]
        
        # Social media links
        social_patterns = {
            'facebook': r'facebook\.com/[\w.-]+',
            'twitter': r'twitter\.com/[\w.-]+',
            'linkedin': r'linkedin\.com/(?:company|in)/[\w.-]+',
            'instagram': r'instagram\.com/[\w.-]+',
            'youtube': r'youtube\.com/(?:c|channel|user)/[\w.-]+'
        }
        
        contact["social_media"] = {}
        for platform, pattern in social_patterns.items():
            links = soup.find_all('a', href=re.compile(pattern, re.I))
            if links:
                contact["social_media"][platform] = links[0]['href']
        
        # Address
        address_keywords = ['adres', 'address', 'konum', 'location']
        for keyword in address_keywords:
            address_elements = soup.find_all(text=re.compile(keyword, re.I))
            for elem in address_elements:
                parent = elem.parent
                if parent:
                    address_text = parent.get_text(strip=True)
                    if len(address_text) > 20 and len(address_text) < 300:
                        contact["address"] = address_text
                        break
            if contact.get("address"):
                break
        
        # Contact page link
        contact_links = soup.find_all('a', href=re.compile(r'contact|iletisim|bize.*ulas', re.I))
        contact["contact_page_urls"] = [urljoin(url, link['href']) for link in contact_links[:3]]
        
        return contact