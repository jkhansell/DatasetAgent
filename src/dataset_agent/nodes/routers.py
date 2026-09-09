from dataset_agent.agents.state import DatasetState

def end_router(state: DatasetState):
    config = state.get("config", {})
    max_rescrape = config.get("rescrape_steps", 0)
    target_sources = config.get("target_sources", 5)

    if state["step_count"] < state["max_steps"]:
        if state["current_sources"] <= target_sources:
            return "summary"
        else:
            return "loop"

    if state["rescrape_step_count"] < max_rescrape and state["step_count"] >= state["max_steps"]:
        return "rescrape"

    return "summary"
