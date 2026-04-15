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

def save_router(state: DatasetState):
    # Route back to where we came from or END
    phase = state.get("phase", "discover")
    if phase == "discover":
        return "rescrape"
    if phase == "rescrape":
        return "extract_kb"
    if phase == "extract_kb":
        return "end"
    
    return "end"
