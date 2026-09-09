import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from a YAML or JSON file.
    """
    import yaml
    import json

    path = Path(config_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    with open(path, "r") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        elif path.suffix == ".json":
            return json.load(f)
        else:
            # Default to YAML
            return yaml.safe_load(f)


def get_default_config() -> dict:
    """
    Returns default configuration.
    """
    return {
        "llm": {
            "base_url": os.getenv("OPENAI_BASE_URL", "http://localhost:9001/v1"),
            "model_name": os.getenv("MODEL_NAME", "Qwen3.5"),
            "temperature": 0.3,
        },
        "max_steps": 50,
        "rescrape_steps": 5,
        "target_sources": 50,
        "target_datasets": 30,
        "dataset_goal": "leukocyte / white blood cell labeled datasets for segmentation, classification and identification",
        "prompts": {
            "discovery_human": """
Search for datasets about {dataset_goal} and return the results when you find 5.
"""
        },
        "summary_output_path": "data/summary.md",
    }
