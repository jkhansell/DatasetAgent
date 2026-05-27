from typing import Dict
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

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