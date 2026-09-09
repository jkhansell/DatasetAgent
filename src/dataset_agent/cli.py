"""
CLI entry point for the Dataset Agent.
"""

import argparse
import json
import sys

from dataset_agent.graph import run_agent
from dataset_agent.utils.config import load_config, get_default_config


def main():
    parser = argparse.ArgumentParser(description="Dataset Agent - Autonomous dataset discovery")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument("--goal", type=str, default=None, help="Dataset discovery goal (overrides config)")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum number of steps")
    parser.add_argument("--target-sources", type=int, default=None, help="Target number of sources")

    args = parser.parse_args()

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        print("Using default config...")
        config = get_default_config()

    # Override with CLI args
    if args.goal:
        config["dataset_goal"] = args.goal
    if args.max_steps:
        config["max_steps"] = args.max_steps
    if args.target_sources:
        config["target_sources"] = args.target_sources

    # Run agent
    print(f"Starting Dataset Agent...")
    print(f"Goal: {config.get('dataset_goal', 'Unknown')}")
    print(f"Max steps: {config.get('max_steps', 10)}")
    print(f"Target sources: {config.get('target_sources', 15)}")
    print()

    try:
        result = run_agent(config)
        print("\nAgent completed successfully!")
        print(f"Final summary: {result.get('final_summary', 'N/A')}")
    except Exception as e:
        print(f"\nError running agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
