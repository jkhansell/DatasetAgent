import json
from langchain.messages import ToolMessage, AIMessage
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Optional, List

def log_section(title):
    print(f"\n{'='*20} {title} {'='*20}")

def debug_state(state):
    print("\n--- STATE SNAPSHOT ---")
    print(f"Phase: {state['phase']}")
    print(f"Step: {state['step_count']}/{state['max_steps']}")
    print(f"Candidate links: {len(state['candidate_links'])}")
    print(f"Downloaded: {len(state['downloaded_links'])}")
    print(f"Preprocessed: {state['preprocessed']}")
    print("----------------------\n")

def debug_messages(result):
    if "messages" not in result:
        return

    log_section("AGENT TRACE")

    for msg in result["messages"]:
        print(f"\n[{msg.type.upper()}]")
        if msg.content:
            print(msg.content)

def extract_tool_results(result, tool_name):
    outputs = {}

    for msg in result["messages"]:
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            outputs[msg.id] = msg.content

    return outputs

def extract_AI_results(result, tool_name):
    outputs = {}

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            outputs[msg.id] = msg.content

    return outputs

def extract_all_urls(result) -> List[str]:
    """
    Extract all URLs from search_datasets and scrape_website tool outputs.
    """
    urls = []
    
    for msg in result.get("messages", []):
        if not isinstance(msg, ToolMessage):
            continue
            
        try:
            content = json.loads(msg.content)
            
            # 1. From search_datasets (Tavily format)
            if msg.name == "search_datasets" and isinstance(content, dict):
                # Tavily results are usually in a 'results' list
                search_results = content.get("results", [])
                for r in search_results:
                    if isinstance(r, dict) and "url" in r:
                        urls.append(r["url"])
            
            # 2. From scrape_website (Scrapy format)
            elif msg.name == "scrape_website" and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "links" in item:
                        # item['links'] is a list of URLs
                        urls.extend(item["links"])
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                        
        except (json.JSONDecodeError, TypeError):
            continue
            
    return list(set(urls)) # deduplicate

def load_jl(path):
    import json
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def load_config(config_path="configs/dataset_agent.yaml"):
    import yaml
    import os
    
    # Try alternate path if not found (e.g. if run from state_agent directory)
    if not os.path.exists(config_path):
        alt_path = os.path.join("..", config_path)
        if os.path.exists(alt_path):
            config_path = alt_path

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


class DatasetEntry(BaseModel):
    """Individual dataset record metadata."""
    # Required fields
    iid: str = Field(description="Internal unique identifier for the dataset record.")
    url: str = Field(description="Dataset source URL.")
    title: str = Field(description="Dataset title.")
    description: str = Field(description="Dataset extensive description.")
    repository: str = Field(description="Dataset repository or platform (kaggle, github, etc.).")
    task: str = Field(description="Primary task the dataset is suited for (segmentation, classification, etc.).")
    annotation_type: str = Field(description="Type of annotation provided.")
    number_images: int = Field(description="Number of images in dataset.")
    dimensions: str = Field(description="Image dimensions or resolution format.")

    # Optional fields using the Optional keyword
    source: Optional[str] = Field(default=None, description="Dataset source platform or origin.")
    
    # Using alias so LLM can provide 'license' and we map it to 'license_'
    license_: Optional[str] = Field(
        default=None, 
        alias="license", 
        description="Dataset license."
    )
    
    raw_metadata: Optional[str] = Field(default=None, description="Unstructured extracted metadata if there is metadata be through (JSON string recommended).")

    # This allows the model to be created using 'license' or 'license_'
    model_config = ConfigDict(populate_by_name=True)

class DatasetDiscoveryOutput(BaseModel):
    """Batch of dataset metadata entries indexed by unique identifier."""
    entries: Dict[str, DatasetEntry] = Field(
        description="Dictionary of dataset records keyed by iid."
    )