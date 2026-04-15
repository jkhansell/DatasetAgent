import scrapy
from urllib.parse import urljoin

class DatasetSpider(scrapy.Spider):
    name = "dataset_spider"

    custom_settings = {
        "FEEDS": {
            "output.json": {
                "format": "json",
                "indent": 2,
            }
        }
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [start_url]

    def parse(self, response):
        self.logger.info(f"Parsing: {response.url}")

        # Extract links, filtering out PDFs and other binary formats
        links = response.css("a::attr(href)").getall()
        links = [urljoin(response.url, l) for l in links if l]
        
        excluded_exts = [".pdf", ".jpg", ".png", ".jpeg", ".mp4", ".doc", ".docx"]
        links = [l for l in links if not any(l.lower().endswith(ext) for ext in excluded_exts)]

        # Extract text content (clean) - use more specific selectors for depth
        paragraphs = response.css("p::text, h1::text, h2::text, h3::text, li::text").getall()
        text = " ".join(p.strip() for p in paragraphs if p.strip())

        # Extract metadata
        title = response.css("title::text").get()
        meta_description = response.css('meta[name="description"]::attr(content)').get()

        yield {
            "url": response.url,
            "title": title,
            "meta_description": meta_description,
            "text": text[:10000],  # balancing context and token usage
            "links": list(set(links)),  # deduplicate
        }
