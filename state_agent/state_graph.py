# ==========================================
# 0. IMPORTS 
# ==========================================
from dotenv import load_dotenv
load_dotenv()

from typing import Dict
from langgraph.graph import StateGraph, END

from utils.config import load_config
from utils.types import DatasetState
from utils.db import init_db, load_from_db, save_to_db

# Import Nodes
from nodes.discovery import discovery_node
from nodes.extract import extract_kb_node
from nodes.rescrape import rescrape_node
from nodes.save import save_node

# Import Routers
from utils.routers import (
    discovery_router,
    save_router
)

config = load_config()

# ==========================================
# 1. INITIALIZATION
# ==========================================

def init_state(sources: Dict = None, num_datasets: int = None) -> DatasetState:
    if sources is None:
        sources = {}
    
    if num_datasets is None:
        num_datasets = config.get("target_sources", 1)

    return {
        "dataset_name": "wbc_dataset",
        "phase": "discover",
        "step_count": 0,
        "max_steps": config.get("max_steps", 50),
        "target_sources": num_datasets,
        "sources": sources,
        "candidate_urls": [],
        "dataset_kb": "",
        "history": [],
    }

# ==========================================
# 2. GRAPH CONSTRUCTION
# ==========================================

builder = StateGraph(DatasetState)

builder.set_entry_point("discover")

builder.add_node("discover", discovery_node)
builder.add_node("extract_kb", extract_kb_node)
builder.add_node("rescrape", rescrape_node)
builder.add_node("save", save_node)

builder.add_conditional_edges("discover", discovery_router, {
    "discover": "discover",
    "save": "save",
})

builder.add_edge("rescrape", "save")
builder.add_edge("extract_kb", "save")

builder.add_conditional_edges("save", save_router, {
    "rescrape": "rescrape",
    "extract_kb": "extract_kb",
    "end": END
})

graph = builder.compile()

# ==========================================
# 3. RUN
# ==========================================

if __name__ == "__main__":
    import sys
    n_datasets = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Restart capabilities
    init_db()
    loaded_sources = load_from_db()

    state = init_state(loaded_sources, num_datasets=n_datasets)
    final_state = graph.invoke(state)
        
    save_to_db(final_state)
    print("✅ Database populated with dataset URLs and metadata.")
