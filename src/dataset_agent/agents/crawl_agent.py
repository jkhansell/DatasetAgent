from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from dataset_agent.utils.logging import get_logger

logger = get_logger(__name__)

@tool
def visit_url(url: str) -> str:
    """Visit the given URL and return the content."""
    return ""

def build_agent(llm):
    """
    Builds a LangGraph ReAct agent with visit_url tool.
    """

    return create_react_agent(
        model=llm,
        tools=[visit_url],
    )
