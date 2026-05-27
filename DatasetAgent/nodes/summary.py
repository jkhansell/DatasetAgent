import json
import os
from langchain_core.messages import SystemMessage, HumanMessage

from DatasetAgent.utils.logging import log_section, get_logger
from DatasetAgent.utils.llm import get_LLM
from DatasetAgent.agents.state import DatasetState
from DatasetAgent.db.db import get_datasets
from DatasetAgent.agents.prompts import SUMMARY_SYSTEM

logger = get_logger(__name__)

def summary_node(state: DatasetState):

    log_section("NODE: SUMMARY")
    state["phase"] = "summary"

    db = state["db"]
    config = state["config"]

    datasets = get_datasets(db)
    
    # If no datasets were found, just return without hitting the LLM
    if not datasets:
        summary_text = "No datasets were recorded in the database during this run."
        logger.info(summary_text)
        return {
            "phase": "summary",
            "final_summary": summary_text
        }

    dataset_goal = state.get("dataset_goal", "Unknown context/goal")

    llm = get_LLM(
        base_url=config.get("llm", {}).get("base_url", ""),
        model_name=config.get("llm", {}).get("model_name", "gpt-4"),
        temperature=0.1,
    )
    
    system_prompt = SUMMARY_SYSTEM.format(dataset_goal=dataset_goal)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Newly discovered datasets JSON:\n{json.dumps(datasets, indent=2)}")
    ]

    logger.info("⏳ Agent is thinking (summary)...")
    try:
        result = llm.invoke(messages)
        final_summary = result.content
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        final_summary = "An error occurred while generating the summary."

    logger.info(f"Final Summary generated:\n{final_summary}")
    
    output_path = config.get("summary_output_path", "data/summary.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_summary)
        logger.info(f"💾 Summary written to {output_path}")
    except Exception as e:
        logger.error(f"Error writing summary to file: {e}")

    return {
        "phase": "summary",
        "final_summary": final_summary
    }
