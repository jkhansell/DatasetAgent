import yaml
import os

def load_config(config_path="configs/dataset_agent.yaml"):
    """
    Load the agent configuration from a YAML file.
    Handles relative path resolution for different run contexts.
    """
    # Try alternate path if not found (e.g. if run from state_agent or state_agent/utils directory)
    if not os.path.exists(config_path):
        # Check parent and grandparent directories
        alt_paths = [
            os.path.join("..", config_path),
            os.path.join("..", "..", config_path)
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                config_path = alt
                break

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
