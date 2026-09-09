# ==========================================
# 0. IMPORTS
# ==========================================
from dotenv import load_dotenv

load_dotenv()

from typing import Dict
from langgraph.graph import StateGraph, END

from dataset_agent.agents.state import DatasetState

from dataset_agent.db.db import init_db, load_db, save_db, DB_PATH

# Import Nodes
from dataset_agent.nodes.discovery import discovery_node
from dataset_agent.nodes.crawl_extract import crawl_extract_node
from dataset_agent.nodes.resolve_datasets import resolve_datasets_node
from dataset_agent.nodes.summary import summary_node
from dataset_agent.nodes.routers import end_router

# ==========================================
# 2. GRAPH CONSTRUCTION
# ==========================================


def build_graph():

    builder = StateGraph(DatasetState)

    builder.set_entry_point("discover")

    builder.add_node("discover", discovery_node)
    builder.add_node("crawl_extract", crawl_extract_node)
    builder.add_node("resolve_datasets", resolve_datasets_node)
    builder.add_node("summary", summary_node)

    builder.add_edge("discover", "crawl_extract")
    builder.add_edge("crawl_extract", "resolve_datasets")
    builder.add_conditional_edges(
        "resolve_datasets",
        end_router,
        {
            "loop": "discover",
            "rescrape": "crawl_extract",
            "summary": "summary"
        }
    )

    builder.add_edge("summary", END)
    builder.set_finish_point("summary")

    graph = builder.compile()

    return graph
