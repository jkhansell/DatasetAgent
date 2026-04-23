from typing import List, Dict, Optional, TypedDict
import os
import json
import uuid
import subprocess
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool


from DatasetAgent.utils.logging import log_section, debug_state, debug_messages
from DatasetAgent.utils.parsing import load_jl
from DatasetAgent.utils.config import load_config

config = load_config()

# ==========================================
# Structured Output Schema
# ==========================================

from typing import List, Optional
from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Individual crawl result metadata"""

    entity_type: str = Field(
        description="Type of entity (dataset, paper, repository, tool, portal, collection)"
    )

    title: str = Field(
        description="Primary title of the discovered entity"
    )

    description: Optional[str] = Field(
        description="Short abstract or summary"
    )

    license_: Optional[str] = Field(
        description="Usage license (CC-BY, MIT, proprietary, unknown)"
    )

    doi: Optional[str] = Field(
        description="Digital Object Identifier if available"
    )

    publisher: Optional[str] = Field(
        description="Publishing organization or institution"
    )

    access_level: Optional[str] = Field(
        description="open, restricted, request, subscription, unknown"
    )

    keywords: List[str] = Field(
        default_factory=list,
        description="Relevant keywords or tags"
    )


@tool
def scrape_website(
    url: str,
    max_pages: int = 7,
    min_score: int = 3,
    timeout: int = 60
) -> List[Dict]:
    """
    Focused dataset-discovery crawl of a website using Scrapy.

    Returns ranked high-value pages useful for downstream entity extraction.
    """

    log_section("TOOL: scrape_website")
    print(f"URL: {url}")

    output_file = f"/tmp/scrape_{uuid.uuid4()}.jl"

    cmd = [
        "scrapy",
        "runspider",
        "./scripts/dataset_discovery_spider.py",
        "-a", f"start_url={url}",
        "-a", f"max_pages={max_pages}",
        "-o", output_file,
    ]

    try:
        subprocess.run(
            cmd,
            timeout=timeout,
            check=True,
            capture_output=True,
            text=True
        )

    except subprocess.TimeoutExpired:
        print("Scraping timed out")
        return []

    except subprocess.CalledProcessError as e:
        print("Scraping failed")
        print(e.stderr[:1000] if e.stderr else "")
        return []

    if not os.path.exists(output_file):
        return []

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except Exception:
        data = []

    try:
        os.remove(output_file)
    except Exception:
        pass

    if not data:
        return []

    # ----------------------------------
    # Normalize + filter
    # ----------------------------------
    cleaned = []

    seen = set()

    for row in data:
        url_ = row.get("url")
        if not url_ or url_ in seen:
            continue

        seen.add(url_)

        score = row.get("score", 0)

        if score < min_score:
            continue

        cleaned.append({
            "url": url_,
            "title": row.get("title"),
            "description": row.get("description"),
            "entity_type": row.get("entity_type", "generic"),
            "score": score,
            "downloads": row.get("downloads", []),
            "jsonld": row.get("jsonld", []),
            "headings": row.get("headings", []),
        })

    cleaned.sort(
        key=lambda x: (
            x["score"],
            len(x.get("downloads", [])),
            len(x.get("jsonld", []))
        ),
        reverse=True
    )

    cleaned = cleaned[:max_pages]

    print(f"Returned {len(cleaned)} ranked pages (from {len(data)})")

    return cleaned


# ==========================================
# LLM
# ==========================================
llm = ChatOpenAI(
    base_url=config["llm"]["base_url"],
    api_key="EMPTY",
    model=config["llm"]["model_name"],
    temperature=config["llm"]["temperature"],
)
# ==========================================
# AGENT
# ==========================================
def build_agent(llm): 
    return create_agent(
    model=llm,
    tools=[
        scrape_website,
    ],
    response_format=ToolStrategy(Observation),
)
