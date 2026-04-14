import json
from typing import List
from langchain_core.messages import ToolMessage, AIMessage

def extract_tool_results(result, tool_name):
    outputs = {}
    for msg in result.get("messages", []):
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            outputs[msg.id] = msg.content
    return outputs

def extract_AI_results(result, tool_name):
    outputs = {}
    for msg in result.get("messages", []):
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
                search_results = content.get("results", [])
                for r in search_results:
                    if isinstance(r, dict) and "url" in r:
                        urls.append(r["url"])
            
            # 2. From scrape_website (Scrapy format)
            elif msg.name == "scrape_website" and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "links" in item:
                        urls.extend(item["links"])
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                        
        except (json.JSONDecodeError, TypeError):
            continue
            
    return list(set(urls)) # deduplicate

def load_jl(path):
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data
