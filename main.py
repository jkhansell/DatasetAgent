import sys
import os
import yaml
import argparse

from scripts.wait_for_server import wait_for_server
from scripts.visualize_connections import make_visualization

from DatasetAgent.state_graph import build_graph
from DatasetAgent.agents.state import init_state
from DatasetAgent.db.db import save_db
from DatasetAgent.utils.logging import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run the DatasetAgent workflow.")
    parser.add_argument(
        "--config", 
        type=str, 
        default="configs/dataset_agent.yaml",
        help="Path to the configuration YAML file."
    )
    parser.add_argument(
        "--target", 
        type=int, 
        help="Target number of datasets (overrides config)."
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=300,
        help="Timeout in seconds for vLLM readiness check."
    )
    
    args = parser.parse_args()

    logger.info(f"🚀 Starting DatasetAgent using config: {args.config}")
    
    with open(args.config, 'r') as f:
        local_config = yaml.safe_load(f)

    # 1. Wait for vLLM
    base_url = local_config["llm"]["base_url"]
    model_name = local_config["llm"]["model_name"]
    
    if not wait_for_server(base_url, model_name, timeout=args.timeout):
        logger.error("❌ Failed to connect to vLLM. Exiting.")
        sys.exit(1)
        
    # 2. Get target sources
    n_datasets = args.target if args.target is not None else local_config.get("target_sources", 1)
    
    logger.info(f"🎯 Target: {n_datasets} datasets.")
    

    state = init_state(local_config)
    
    graph = build_graph()
    
    # 4. Run Graph
    logger.info("⚡ Running the state graph...")
    final_state = graph.invoke(state)
        
    # 5. Save results
    save_db(final_state["db"])

    logger.info("✅ Database populated with new datasets.")

    make_visualization()

if __name__ == "__main__":
    main()
