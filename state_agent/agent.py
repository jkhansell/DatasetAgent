from typing import List, Dict, Optional, TypedDict
from typing import Union
import subprocess, json, os, uuid

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool

from tavily import TavilyClient

from utils.logging import log_section, debug_state, debug_messages
from utils.parsing import load_jl
from utils.models import (
    DatasetEntry, 
    DatasetDiscoveryOutput
)
from utils.config import load_config

tavily = TavilyClient()
config = load_config()

@tool
def search_datasets(query: str, exclude_domains: List[str]):
    """
    Search for dataset-related links using a query string.

    Args:
        query (str): Search keywords describing the dataset.
        exclude_domains (List[str]): Excluded domains in the search.

    Returns:
        List[str]: List of URLs returned by the search engine.
    """
    log_section("TOOL: search_datasets")
    results = tavily.search(query, exclude_domains=exclude_domains)

    return results

@tool
def run_shell(command: str) -> str:
    """
    Execute a shell command and capture its output.

    Args:
        command (str): Shell command to execute.

    Returns:
        str: Combined stdout and stderr from the command.
    """
    log_section("TOOL: run_shell")
    print(f"Command: {command}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    return result.stdout + result.stderr



@tool
def scrape_website(url: str) -> dict:
    """
    Scrape a webpage for structured data using a Scrapy spider.

    Args:
        url (str): Target webpage URL.

    Returns:
        dict: Extracted structured data including discovered links.
    """
    log_section("TOOL: scrape_website")
    print(f"URL: {url}")


    output_file = f"/tmp/temp_scrape_{uuid.uuid4()}.jl"

    cmd = f"scrapy runspider ./scripts/spider.py -a start_url={url} -o {output_file}"
    
    subprocess.run(cmd, shell=True)

    if not os.path.exists(output_file):
        return {}

    with open(output_file) as f:
        data = load_jl(output_file)

    if os.path.exists(output_file):
        os.remove(output_file)

    if data:
        print(f"Scraped {len(data)} links")
        return data

    return {}


# ==========================================
# 3. LLM
# ==========================================
llm = ChatOpenAI(
    base_url=config["llm"]["base_url"],
    api_key="EMPTY",
    model=config["llm"]["model_name"],
    temperature=config["llm"]["temperature"],
)
from langgraph.checkpoint.memory import InMemorySaver  
# ==========================================
# 5. AGENT
# ==========================================
discovery_agent = create_agent(
    model=llm,
    tools=[
        search_datasets,
        scrape_website,
        run_shell,
    ],
    response_format=ToolStrategy(DatasetDiscoveryOutput),
)

knowledge_agent = create_agent(
    model=llm,
    tools=[
        run_shell
    ],
)
