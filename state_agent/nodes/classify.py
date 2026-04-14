from langchain_core.messages import HumanMessage, SystemMessage
from agent import classification_agent
from utils.logging import log_section
from utils.config import load_config
from utils.types import DatasetState

config = load_config()

def classify_node(state: DatasetState):
    log_section("NODE: CLASSIFY")
    state["phase"] = "classify"

    sources = state["sources"].copy()
    
    # Filter for entries that need classification
    to_classify = {iid: entry for iid, entry in sources.items() if entry.download_status == "pending"}
    
    if not to_classify:
        print("No new sources to classify.")
        return {"sources": sources}

    print(f"Classifying {len(to_classify)} sources...")
    
    messages = [
        SystemMessage(content=config["prompts"]["classify"]),
        HumanMessage(content=config["prompts"]["classify_human"].format(
            sources=str(to_classify)
        ))
    ]
    
    result = classification_agent.invoke({"messages": messages})
    
    if "structured_response" in result:
        for cls in result["structured_response"].classifications:
            # Find the matching entry based on URL
            match = next((e for e in to_classify.values() if e.url == cls.url), None)
            if match:
                match.downloader_type = cls.source_type
                match.downloader_id = cls.identifier
                match.confidence = cls.confidence
                
                if cls.source_type == "none" or cls.confidence < config.get("confidence_threshold", 0.7):
                    # Flag for rescrape if confidence is low or none
                    match.download_status = "low_confidence"
                    print(f"⚠️ Low confidence for {match.url} ({cls.confidence}). Flagged for rescrape.")
                else:
                    match.download_status = "classified"
                    print(f"✅ Classified {match.url} as {cls.source_type}")

    return {"sources": sources}
