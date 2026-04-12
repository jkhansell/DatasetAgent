# ==========================================
# 0. IMPORTS
# ==========================================

from dotenv import load_dotenv
load_dotenv()

from typing import List, Dict, Optional
import sqlite3
from pathlib import Path

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from langchain.agents import AgentState

from agent import discovery_agent, knowledge_agent
import pprint

from utils import (
    log_section, 
    debug_messages, 
    extract_tool_results,
    extract_all_urls,
    load_config,
    DatasetEntry, 
    DatasetDiscoveryOutput
)

config = load_config()

# ==========================================
# 1. STATE
# ==========================================

class DatasetState(AgentState):
    dataset_name: Optional[str]

    phase: str
    step_count: int
    max_steps: int
    target_sources: int
    num_old_sources: int
    sources: Dict           # entries
    candidate_urls: List[str] # urls found but not yet curated
    dataset_kb: str         # path to dataset knowledge base(json, csv, etc.)

    history: List[str]

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
    }

# ==========================================
# 2. DATABASE SETUP
# ==========================================

DB_PATH = "./data/datasets.db"


db_string = """
    iid TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    description TEXT,
    repository TEXT,
    task TEXT,
    annotation_type TEXT,
    source TEXT,
    license TEXT,
    raw_metadata TEXT,
    number_images INTEGER,
    dimensions TEXT

"""


# ==========================================
# 3. NODES
# ==========================================


def discovery_node(state: DatasetState):
    log_section("NODE: DISCOVERY")

    sources = {entry.iid: entry for entry in state["sources"].values()}
    urls = [entry.url for entry in state["sources"].values()]

    if len(urls) > state["target_sources"]:
        print(f"Already have {len(urls)} sources, which is above the target of {state['target_sources']}. Skipping discovery.")
        return {"sources": sources}
    
    messages = [
        SystemMessage(content=config["prompts"]["discovery"]),
        HumanMessage(content=config["prompts"]["discovery_human"].format(
            target_sources=state['target_sources'],
            urls=urls,
            candidate_urls=state.get("candidate_urls", []),
            db_string=db_string
        ))
    ]

    result = discovery_agent.invoke({"messages": messages})

    print("===== RAW OUTPUT =====")
    with open("./raw_output.txt", "w") as f:
        pprint.pprint(result, f)

    if "structured_response" in result:
        sources.update(result["structured_response"].entries)

    # Programmatically extract all candidate URLs from tool outputs
    new_candidate_urls = extract_all_urls(result)
    updated_candidates = list(set(state.get("candidate_urls", []) + new_candidate_urls))

    return {
        "sources": sources,
        "candidate_urls": updated_candidates
    }

def extract_kb_node(state: DatasetState):
    log_section("NODE: EXTRACT KB")

    messages = [
        SystemMessage(content=config["prompts"]["summary"]),
        HumanMessage(content=config["prompts"]["summary_human"].format(
            sources=state['sources']
        ))
    ]

    result = knowledge_agent.invoke({"messages": messages})
    debug_messages(result)

    return {"dataset_kb": "data/summary.md"}
    
# ==========================================
# 4. ROUTERS
# ==========================================

def discovery_router(state: DatasetState):
    if len(state["sources"].keys()) > 0:
        results = [entry for entry in state["sources"]]
        if len(results) < state["target_sources"]:
            return "discover"
    else: 
        return "discover"

    return "extract_kb"

def extract_kb_router(state: DatasetState):
    if not state["dataset_kb"]:
        return "extract_kb"
    return END

# ==========================================
# 5. GRAPH
# ==========================================

builder = StateGraph(DatasetState)

builder.set_entry_point("discover")

builder.add_node("discover", discovery_node)
builder.add_node("extract_kb", extract_kb_node)

builder.add_conditional_edges("discover", discovery_router, {
    "discover": "discover",
    "extract_kb": "extract_kb",
})
    
builder.set_finish_point("extract_kb")

graph = builder.compile()

# ==========================================
# 7. SQLITE
# ==========================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"CREATE TABLE IF NOT EXISTS datasets ({db_string});")

    conn.commit()
    return conn

def load_from_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM datasets")
    rows = cursor.fetchall()
    
    mapped_entries = {}

    for row in rows:
        # 1. Convert row to dict
        row_dict = dict(row)
        
        # 2. Validate and restore the Pydantic model
        entry = DatasetEntry.model_validate(row_dict)
        
        # 3. Map it to its iid
        mapped_entries[entry.iid] = entry

    conn.close()
    return mapped_entries

def save_to_db(state):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for entry in state["sources"].values():
        cursor.execute("""
            INSERT OR IGNORE INTO datasets (
                iid, 
                url,
                title,
                description,
                repository,
                task,
                annotation_type,
                source,
                license,
                raw_metadata,
                number_images,
                dimensions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.iid,
            entry.url,
            entry.title,
            entry.description,
            entry.repository,
            entry.task,
            entry.annotation_type,
            entry.source,
            entry.license_,
            entry.raw_metadata,
            entry.number_images,
            entry.dimensions,
        ))

    conn.commit()
    conn.close()

# ==========================================
# 8. RUN
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
