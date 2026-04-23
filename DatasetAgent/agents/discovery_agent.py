from typing import List, Dict, Optional, TypedDict
import os
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool

from DatasetAgent.utils.logging import log_section, debug_state, debug_messages
from DatasetAgent.utils.parsing import load_jl
from DatasetAgent.utils.config import load_config

# ==========================================
# Structured Output Schema
# ==========================================

class Search(BaseModel):
    """Individual search record metadata."""
    # Required fields
    iid: str = Field(description="Internal unique identifier for the dataset record.")
    query: str = Field(description="Query used for Tavily search.")
    topic: str = Field(description="Topic of the query used.")

class SearchOutput(BaseModel):
    """Batch of search metadata entries indexed by unique identifier."""
    entries: Dict[str, Search] = Field(
        description="Dictionary of search records keyed by iid."
    )

# ==========================================
# AGENT
# ==========================================

def build_agent(llm):
    return create_agent(
        model=llm,
        response_format=ToolStrategy(SearchOutput),
    )