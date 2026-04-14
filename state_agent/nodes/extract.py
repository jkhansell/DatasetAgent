from langchain_core.messages import HumanMessage, SystemMessage
from agent import knowledge_agent
from utils.logging import log_section
from utils.config import load_config
from utils.types import DatasetState

config = load_config()

def extract_kb_node(state: DatasetState):
    log_section("NODE: EXTRACT KB")
    state["phase"] = "extract_kb"
    
    messages = [
        SystemMessage(content=config["prompts"]["summary"]),
        HumanMessage(content=config["prompts"]["summary_human"].format(
            sources=state["sources"]
        ))
    ]
    
    result = knowledge_agent.invoke({"messages": messages})
    
    # We could extract path from result, for now just use a placeholder
    return {"dataset_kb": "./data/discovered_kb.json"}
