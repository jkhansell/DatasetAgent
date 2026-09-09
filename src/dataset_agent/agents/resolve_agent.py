from typing import Dict
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ResolveOutput(BaseModel):
    """Output schema for dataset resolution."""
    same_dataset: bool = Field(description="Whether the observation refers to the same dataset.")
    confidence: float = Field(description="Confidence score between 0 and 1.")
    reasoning: str = Field(description="Reasoning string.")

def build_agent(llm):
    return create_agent(
        model=llm,
        response_format=ToolStrategy(ResolveOutput),
    )
