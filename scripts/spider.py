import json
import re
import hashlib
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import scrapy
from scrapy_playwright.page import PageMethod


class DatasetEvidenceSpider(scrapy.Spider):
    name = "dataset_evidence"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DEPTH_LIMIT": 5,
        "DOWNLOAD_DELAY": 0.25,
        "AUTOTHROTTLE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_TIMEOUT": 60*10,
        "RETRY_TIMES": 2,
        "LOG_LEVEL": "INFO",

        "TWISTED_REACTOR":
            "twisted.internet.asyncioreactor.AsyncioSelectorReactor",

        "DOWNLOAD_HANDLERS": {
            "http":
                "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https":
                "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },

        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,
    }

    FILE_EXTS = (
        ".csv", ".json", ".geojson", ".parquet", ".nc",
        ".h5", ".hdf5", ".zip", ".tar.gz", ".gpkg", ".tif"
    )

    def __init__(self, start_url=None, max_pages=40, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not start_url:
            raise ValueError("start_url required")

        self.start_urls = [start_url]
        self.allowed_domains = [urlparse(start_url).netloc]
        self.max_pages = int(max_pages)

        self.seen = set()
        self.count = 0

    # -------------------------------------------------
    # Start
    # -------------------------------------------------
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 2000),
                    ]
                }
            )

    # -------------------------------------------------
    # MAIN PARSER (UPGRADED)
    # -------------------------------------------------
    async def parse(self, response):
        if self.count >= self.max_pages:
            await self.safe_close(response)
            return

        page = response.meta.get("playwright_page")

        # -------- Scroll for lazy content --------
        if page:
            try:
                await page.evaluate("""
                    async () => {
                        for (let i = 0; i < 5; i++) {
                            window.scrollBy(0, document.body.scrollHeight);
                            await new Promise(r => setTimeout(r, 800));
                        }
                    }
                """)
            except Exception:
                pass

        # -------- Canonical / dedup --------
        url = self.canonicalize(response.url)
        if url in self.seen:
            await self.safe_close(response)
            return

        self.seen.add(url)
        self.count += 1

        # -------- Full DOM text --------
        text_nodes = response.xpath(
            "//body//text()[not(ancestor::script) and not(ancestor::style)]"
        ).getall()

        clean_nodes = [self.clean(t) for t in text_nodes if self.clean(t)]
        full_text = " ".join(clean_nodes)[:15000]

        # -------- JS runtime extraction --------
        js_data = {}
        if page:
            try:
                js_data = await page.evaluate("""
                    () => {
                        const out = {};
                        for (const k in window) {
                            try {
                                const v = window[k];
                                if (typeof v === "object") {
                                    const s = JSON.stringify(v);
                                    if (s && s.length < 20000) {
                                        out[k] = v;
                                    }
                                }
                            } catch(e) {}
                        }
                        return out;
                    }
                """)
            except Exception:
                pass

        # -------- Base evidence --------
        evidence = self.extract_evidence(response)

        evidence["visible_text"] = full_text
        evidence["js_data"] = js_data

        # -------- Embedded dataset links --------
        evidence["embedded_files"] = re.findall(
            r'https?://[^\s]+?\.(csv|json|parquet|nc|zip)',
            full_text,
            re.I
        )

        # -------- Dataset heuristics --------
        evidence["signals"]["dataset_like"] = any(
            re.search(p, full_text, re.I)
            for p in [
                r"\bdataset\b",
                r"\bdata set\b",
                r"\brepository\b",
                r"\bopen data\b",
                r"\bdownload\b",
                r"\bapi\b"
            ]
        )

        # -------- Content hash --------
        evidence["content_hash"] = hashlib.md5(
            full_text.encode()
        ).hexdigest()

        yield evidence

        # -------- Link prioritization --------
        links = self.extract_links(response)

        def score(u):
            return sum(
                k in u.lower()
                for k in ["data", "dataset", "download", "api", "catalog"]
            )

        links = sorted(links, key=score, reverse=True)

        # -------- Crawl --------
        for link in links:
            if self.count >= self.max_pages:
                break

            if not self.should_follow(link):
                continue

            yield scrapy.Request(
                url=link,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 1200),
                    ]
                }
            )

        await self.safe_close(response)

    # -------------------------------------------------
    # Existing helpers (mostly unchanged)
    # -------------------------------------------------
    def extract_evidence(self, response):
        return {
            "url": response.url,
            "domain": urlparse(response.url).netloc,
            "title": self.clean(response.css("title::text").get()),
            "meta_description": self.clean(
                response.css('meta[name="description"]::attr(content)').get()
            ),
            "meta_keywords": self.split_csv(
                response.css('meta[name="keywords"]::attr(content)').get()
            ),
            "jsonld": self.extract_jsonld(response),
            "downloads": self.extract_downloads(response),
            "tables": self.extract_tables(response),
            "headings": response.css("h1::text, h2::text").getall(),
            "paragraphs": response.css("p::text").getall(),
            "signals": {
                "doi": self.find_doi(response.text),
                "license": self.find_license(response.text),
                "publisher_hint": self.find_publisher(response),
            }
        }

    def extract_tables(self, response):
        out = []
        for table in response.css("table")[:3]:
            rows = []
            for tr in table.css("tr")[:10]:
                cells = tr.css("th::text, td::text").getall()
                cells = [self.clean(c) for c in cells if self.clean(c)]
                if cells:
                    rows.append(cells)
            if rows:
                out.append(rows)
        return out

    def extract_downloads(self, response):
        files = []
        for href in response.css("a::attr(href)").getall():
            if not href:
                continue
            full = urljoin(response.url, href)
            if any(full.lower().endswith(ext) for ext in self.FILE_EXTS):
                files.append(full)
        return list(dict.fromkeys(files))[:25]

    def extract_jsonld(self, response):
        blocks = response.css('script[type="application/ld+json"]::text').getall()
        found = []
        for block in blocks:
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    found.extend(data)
                else:
                    found.append(data)
            except:
                try:
                    fixed = re.sub(r",\s*}", "}", block)
                    found.append(json.loads(fixed))
                except:
                    pass
        return found[:10]

    def extract_links(self, response):
        return list(dict.fromkeys([
            self.canonicalize(urljoin(response.url, href))
            for href in response.css("a::attr(href)").getall()
            if href
        ]))

    def should_follow(self, url):
        p = urlparse(url)
        if p.netloc not in self.allowed_domains:
            return False
        if any(url.lower().endswith(ext) for ext in (
            ".jpg", ".png", ".pdf", ".mp4", ".doc"
        )):
            return False
        return True

    def find_doi(self, text):
        m = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)
        return m.group(0) if m else None

    def find_license(self, text):
        text = text.lower()
        for x in ["cc-by", "mit", "apache", "gnu"]:
            if x in text:
                return x
        return None

    def find_publisher(self, response):
        return self.clean(
            response.css('meta[property="og:site_name"]::attr(content)').get()
        )

    async def safe_close(self, response):
        page = response.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass

    def canonicalize(self, url):
        p = urlparse(url)
        query = urlencode([
            (k, v)
            for k, v in parse_qsl(p.query)
            if not k.lower().startswith("utm_")
        ])
        return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", query, ""))

    def clean(self, x):
        if not x:
            return None
        x = re.sub(r"\s+", " ", x).strip()
        return x or None

    def split_csv(self, x):
        if not x:
            return []
        return [i.strip() for i in x.split(",") if i.strip()]