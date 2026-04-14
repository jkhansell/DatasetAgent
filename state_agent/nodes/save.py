from utils.logging import log_section
from utils.db import save_to_db
from utils.types import DatasetState

def save_node(state: DatasetState):
    log_section("NODE: SAVE")
    save_to_db(state)
    print(f"✅ State saved to database ({len(state['sources'])} sources).")
    return state
