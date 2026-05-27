import time
import requests
import sys
import yaml
import os
from DatasetAgent.utils.logging import get_logger

logger = get_logger(__name__)

def wait_for_server(base_url, model_name, timeout=300):
    """
    Wait for LLM server to be ready and have the specified model loaded.
    """
    start_time = time.time()
    url = f"{base_url}/models"
    
    logger.info(f"⏳ Waiting for vLLM at {url} (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                for model in models:
                    if model.get("id") == model_name:
                        logger.info(f"✅ Server is ready! Model '{model_name}' is loaded.")
                        return True
            else:
                logger.warning(f"Server returned status {response.status_code}, still waiting...")
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        logger.info(f"⏳ Still waiting... ({elapsed}s elapsed)")
        
    logger.error("❌ Timeout reached. Server is not ready.")
    return False

if __name__ == "__main__":
    # Load config to get defaults
    config_path = "configs/dataset_agent.yaml"
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    base_url = config["llm"]["base_url"]
    model_name = config["llm"]["model_name"]
    
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
        
    if not wait_for_vllm(base_url, model_name):
        sys.exit(1)
