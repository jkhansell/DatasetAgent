# ==========================================
# 0. IMPORTS 
# ==========================================
from dotenv import load_dotenv
load_dotenv()

from typing import Dict
from langgraph.graph import StateGraph, END

from DatasetAgent.utils.types import DatasetState

from DatasetAgent.db.db import init_db, load_db, save_db, DB_PATH

# Import Nodes
from DatasetAgent.nodes.discovery import discovery_node
from DatasetAgent.nodes.crawl_extract import crawl_extract_node

# Import Routers
from DatasetAgent.nodes.routers import (
    end_router
)

# ==========================================
# 2. GRAPH CONSTRUCTION
# ==========================================

def build_graph():

    builder = StateGraph(DatasetState)

    builder.set_entry_point("discover")

    builder.add_node("discover", discovery_node)
    builder.add_node("crawl_extract", crawl_extract_node)

    builder.add_edge("discover", "crawl_extract")


    builder.set_finish_point("crawl_extract")

    graph = builder.compile()

    return graph
