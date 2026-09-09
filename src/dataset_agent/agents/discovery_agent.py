from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from dataset_agent.utils.logging import get_logger

logger = get_logger(__name__)

@tool
def search(query: str) -> str:
    """Search the web for the given query."""
    return ""

@tool
def visit_url(url: str) -> str:
    """Visit the given URL and return the content."""
    return ""

def build_agent(llm):
    """
    Builds a LangGraph ReAct agent with search and visit_url tools.
    """

    return create_react_agent(
        model=llm,
        tools=[search, visit_url],
    )
