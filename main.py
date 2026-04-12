import sys
import os

# Add state_agent to path so we can import modules correctly
sys.path.append(os.path.join(os.path.dirname(__file__), "state_agent"))

from state_agent.state_graph import graph, init_state, init_db, load_from_db, save_to_db, config
from scripts.wait_for_vllm import wait_for_vllm

import argparse

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

    print(f"🚀 Starting DatasetAgent using config: {args.config}")
    
    # 0. Load config early to get settings
    # Note: state_graph might have already loaded a default config, 
    # so we might need to reload or re-initialize if the path is different.
    # For now, we'll assume the user wants THIS specific config path.
    if args.config != "configs/dataset_agent.yaml":
        # We need to reload the config in the modules or pass it down
        # For simplicity in this script, we'll reload it here
        import yaml
        with open(args.config, 'r') as f:
            local_config = yaml.safe_load(f)
    else:
        local_config = config

    # 1. Wait for vLLM
    base_url = local_config["llm"]["base_url"]
    model_name = local_config["llm"]["model_name"]
    
    if not wait_for_vllm(base_url, model_name, timeout=args.timeout):
        print("❌ Failed to connect to vLLM. Exiting.")
        sys.exit(1)
        
    # 2. Get target sources
    n_datasets = args.target if args.target is not None else local_config.get("target_sources", 1)
    
    # 3. Initialize DB and State
    init_db()
    loaded_sources = load_from_db()
    
    print(f"📊 Initializing state with {len(loaded_sources)} existing records.")
    print(f"🎯 Target: {n_datasets} datasets.")
    
    state = init_state(loaded_sources, num_datasets=n_datasets)
    
    # 4. Run Graph
    print("⚡ Running the state graph...")
    final_state = graph.invoke(state)
        
    # 5. Save results
    save_to_db(final_state)
    print("✅ Database populated with dataset URLs and metadata.")
    print("Check ./data/summary.md for the results.")

if __name__ == "__main__":
    main()
