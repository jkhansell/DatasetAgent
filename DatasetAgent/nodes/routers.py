from langgraph.graph import END
from DatasetAgent.utils.types import DatasetState
from DatasetAgent.utils.config import load_config

config = load_config()

def end_router(state: DatasetState):
    if state["step_count"] >= state["max_steps"]:
        return END
    
    if len(state["sources"]) >= state["target_sources"]:
        return END

    return "discover"

