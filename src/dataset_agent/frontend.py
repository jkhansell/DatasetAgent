"""Notebook-friendly frontend for the DatasetAgent pipeline.

Provides a simple ``run()`` function and a ``DatasetAgentFrontend`` class
that handles server readiness, state initialization, graph building,
pipeline execution, database persistence, and visualization in one call.

Example usage in a notebook::

    from dataset_agent import run
    run(config="configs/dataset_agent.yaml", target=50)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

# Ensure the project root is on sys.path so relative config paths resolve.
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dataset_agent.state_graph import build_graph
from dataset_agent.agents.state import init_state
from dataset_agent.db.db import save_db
from dataset_agent.utils.logging import get_logger
from scripts.wait_for_server import wait_for_server
from scripts.visualize_connections import make_visualization

logger = get_logger(__name__)


class DatasetAgentFrontend:
    """High-level interface for running the DatasetAgent pipeline.

    Parameters
    ----------
    config_path :
        Path to the YAML configuration file.
    callbacks :
        Optional dict of hook functions called at key stages.
        Keys: ``on_server_ready``, ``on_state_init``, ``on_graph_built``,
        ``on_pipeline_start``, ``on_pipeline_end``, ``on_save``,
        ``on_visualize``.
    """

    def __init__(
        self,
        config_path: str = "configs/dataset_agent.yaml",
        callbacks: Optional[Dict[str, Callable]] = None,
    ):
        self.config_path = config_path
        self.callbacks = callbacks or {}

    # -- public API ----------------------------------------------------------

    def run(
        self,
        target: Optional[int] = None,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Execute the full pipeline and return the final state.

        Parameters
        ----------
        target :
            Override ``target_sources`` from the config.
        timeout :
            Seconds to wait for the LLM server.

        Returns
        -------
        The final state dict after the graph completes.
        """
        config = self._load_config()
        if target is not None:
            config["target_sources"] = target

        # 1. Wait for vLLM
        base_url = config["llm"]["base_url"]
        model_name = config["llm"]["model_name"]
        if not wait_for_server(base_url, model_name, timeout=timeout):
            logger.error("Failed to connect to vLLM. Exiting.")
            sys.exit(1)
        self.callbacks.get("on_server_ready", lambda: None)()

        # 2. Initialize state
        state = init_state(config)
        self.callbacks.get("on_state_init", lambda: None)(state)

        # 3. Build graph
        graph = build_graph()
        self.callbacks.get("on_graph_built", lambda: None)(graph)

        # 4. Run pipeline
        logger.info("Running the state graph...")
        self.callbacks.get("on_pipeline_start", lambda: None)(state)
        final_state = graph.invoke(state)
        self.callbacks.get("on_pipeline_end", lambda: None)(final_state)

        # 5. Save results
        save_db(final_state["db"])
        self.callbacks.get("on_save", lambda: None)(final_state["db"])

        logger.info("Database populated with new datasets.")

        # 6. Visualization
        make_visualization()
        self.callbacks.get("on_visualize", lambda: None)()

        return final_state

    # -- internals -----------------------------------------------------------

    def _load_config(self) -> dict:
        path = Path(self.config_path)
        if not path.is_absolute():
            # Resolve relative to current working directory (where the user runs)
            path = Path.cwd() / path
        with open(path, "r") as f:
            return yaml.safe_load(f)


def run(
    config: str = "configs/dataset_agent.yaml",
    target: Optional[int] = None,
    timeout: int = 300,
    callbacks: Optional[Dict[str, Callable]] = None,
) -> Dict[str, Any]:
    """Convenience function to run the full pipeline.

    This is the simplest way to invoke DatasetAgent from a notebook::

        from dataset_agent import run
        run(target=50)
    """
    frontend = DatasetAgentFrontend(config_path=config, callbacks=callbacks)
    return frontend.run(target=target, timeout=timeout)
