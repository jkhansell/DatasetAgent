"""
Graph construction and execution for the Dataset Agent pipeline.
"""

from dataset_agent.state_graph import build_graph
from dataset_agent.agents.state import init_state


def run_agent(config: dict):
    """
    Run the agent with the given configuration.
    """

    graph = build_graph()
    state = init_state(config)

    result = graph.invoke(state)

    return result

__all__ = ["build_graph", "run_agent"]
