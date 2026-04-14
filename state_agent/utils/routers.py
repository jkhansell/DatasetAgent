from langgraph.graph import END
from .types import DatasetState
from .config import load_config

config = load_config()

def discovery_router(state: DatasetState):
    if state["step_count"] >= state["max_steps"]:
        return "save"
    if len(state["sources"]) >= state["target_sources"]:
        return "save"
    return "discover"

def classify_router(state: DatasetState):
    needs_rescrape = any(e.download_status == "low_confidence" and e.rescrape_count < config.get("max_rescrape", 2) for e in state["sources"].values())
    needs_download = any(e.download_status == "classified" for e in state["sources"].values())
    
    if needs_download:
        return "download"
    if needs_rescrape:
        return "rescrape"
    return "end"

def rescrape_router(state: DatasetState):
    return "save"

def download_router(state: DatasetState):
    return "save"

def save_router(state: DatasetState):
    # Route back to where we came from or END
    phase = state.get("phase", "discover")
    if phase == "discover":
        return "extract_kb"
    if phase == "classify":
        # After classify, we either go to rescrape or download
        return classify_router(state)
    if phase == "rescrape":
        return "classify"
    if phase == "download":
        return "end"
    
    return "end"
