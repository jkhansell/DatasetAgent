"""
Dataset Agent - Autonomous dataset discovery and curation.
"""

__version__ = "0.1.0"

from dataset_agent.frontend import run
from dataset_agent.state_graph import build_graph

__all__ = ["run", "build_graph"]
