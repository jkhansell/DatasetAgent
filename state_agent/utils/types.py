from typing import List, Dict, Optional
from langchain.agents import AgentState

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
