from langchain.agents import AgentState
from typing import List, Dict, Optional, TypedDict, Any


class DatasetState(AgentState):
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
    # LOGGING (STRUCTURED, NOT TEXT)
    # =========================
    events: List[Dict[str, Any]]  # structured trace instead of strings