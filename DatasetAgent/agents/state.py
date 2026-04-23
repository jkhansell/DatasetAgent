import sqlite3
from langchain.agents import AgentState
from typing import List, Dict, Optional, TypedDict, Any

from DatasetAgent.db.db import init_db, load_db
from DatasetAgent.utils.embedder import get_embedder


class State(AgentState):

    # =========================
    # DATABASE CONNECTION
    # =========================

    db: sqlite3.Connection

    # =========================
    # CONTROL FLOW
    # =========================
    phase: str                  # discovery | scraping | analysis | enrichment
    step_count: int
    max_steps: int
    target_sources: int

    # =========================
    # CURRENT TASK CONTEXT
    # =========================
    dataset_goal: Optional[str]  # what we are trying to find

    # =========================
    # DISCOVERY OUTPUTS
    # =========================
    search_ids: List[int]        # DB references
    source_ids: List[int]        # DB references
    candidate_urls: List[str]    # not yet inserted or pending crawl

    # =========================
    # SCRAPING OUTPUTS
    # =========================
    observation_ids: List[int]   # extracted entities

    # =========================
    # ANALYSIS OUTPUTS
    # =========================
    matched_dataset_ids: List[int]
    new_dataset_ids: List[int]

    # =========================
    # WORKING MEMORY (LLM ONLY)
    # =========================
    scratchpad: Dict[str, Any]    # ephemeral reasoning

    # =========================
    # EMBEDDING MODEL
    # =========================
    embedder: Any

    config: Dict


def init_state(
    config,
) -> State:
    """
    Initialize agent runtime state.
    """
    
    # Initialize DB 
    if not os.path.exists(DB_PATH):
        db = init_db()
    else: 
        db = load_db(DB_PATH)

    # get embedder

    embedder = get_embedder()

    return {
        # Core
        "db": db,
        "embedder": embedder,

        # Control flow
        "phase": "discovery",
        "step_count": 0,
        "max_steps": config["max_steps"],

        # Current objective
        "dataset_goal": config["dataset_goal"],

        # Discovery outputs
        "search_ids": [],
        "source_ids": [],
        "candidate_urls": [],

        # Scraping outputs
        "observation_ids": [],

        # Analysis outputs
        "matched_dataset_ids": [],
        "new_dataset_ids": [],

        # Working memory
        "scratchpad": {
            "current_query": None,
            "visited_domains": set(),
            "stats": {
                "sources_found": 0,
                "sources_processed": 0,
                "observations_created": 0,
            }
        },
    }