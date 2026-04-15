import pprint, uuid
from langchain_core.messages import HumanMessage, SystemMessage
from agent import discovery_agent
from utils.db import db_string
from utils.logging import log_section
from utils.parsing import extract_all_urls
from utils.config import load_config
from utils.types import DatasetState
import os

config = load_config()

def discovery_node(state: DatasetState):
    log_section("NODE: DISCOVERY")
    state["phase"] = "discover"

    sources = {entry.iid: entry for entry in state["sources"].values()}
    urls = [entry.url for entry in state["sources"].values()]

    if len(urls) >= state["target_sources"]:
        print(f"Already have {len(urls)} sources, which is above the target of {state['target_sources']}. Skipping discovery.")
        return {"sources": sources}
    
    messages = [
        SystemMessage(content=config["prompts"]["discovery"]),
        HumanMessage(content=config["prompts"]["discovery_human"].format(
            target_sources=state['target_sources'],
            urls=urls,
            candidate_urls=state.get("candidate_urls", []),
            db_string=db_string,
            excluded_domains=config.get("excluded_domains")
        ))
    ]

    result = discovery_agent.invoke({"messages": messages})

    print("===== RAW OUTPUT =====")
    raw_output_file = f"./logs/raw_output_{uuid.uuid4()}.txt"
    os.makedirs("./logs", exist_ok=True)
    with open(raw_output_file, "w") as f:
        pprint.pprint(result, f)

    if "structured_response" in result:
        excluded_domains = config.get("excluded_domains", [])
        excluded_extensions = config.get("excluded_extensions", [])
        new_entries = {}
        for iid, entry in result["structured_response"].entries.items():
            # Domain check
            if any(domain.lower() in entry.url.lower() for domain in excluded_domains):
                print(f"🚫 Excluding entry from forbidden domain: {entry.url}")
                continue
            # Extension check
            if any(entry.url.lower().endswith(ext.lower()) for ext in excluded_extensions):
                print(f"🚫 Excluding entry with forbidden extension: {entry.url}")
                continue
            new_entries[iid] = entry
        sources.update(new_entries)

    # Programmatically extract all candidate URLs from tool outputs
    new_candidate_urls = extract_all_urls(result)
    
    # Filter candidate URLs
    filtered_candidates = []
    excluded_domains = config.get("excluded_domains", [])
    excluded_extensions = config.get("excluded_extensions", [])
    
    for url in new_candidate_urls:
        if any(domain.lower() in url.lower() for domain in excluded_domains):
            continue
        if any(url.lower().endswith(ext.lower()) for ext in excluded_extensions):
            continue
        filtered_candidates.append(url)
    
    return {
        "sources": sources, 
        "candidate_urls": list(set(state.get("candidate_urls", []) + filtered_candidates))
    }
