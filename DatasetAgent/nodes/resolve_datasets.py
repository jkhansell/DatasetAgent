from DatasetAgent.utils.logging import log_section, get_logger
from DatasetAgent.utils.llm import get_LLM

logger = get_logger(__name__)

from DatasetAgent.agents.resolve_agent import build_agent
from DatasetAgent.agents.state import DatasetState
from DatasetAgent.agents.prompts import RESOLVE_SYSTEM
from DatasetAgent.db.db import create_dataset, update_dataset_from_observation, update_observation_status

from langchain_core.messages import SystemMessage, HumanMessage


def resolve_datasets_node(state: DatasetState):

    log_section("NODE: RESOLVE_DATASETS")
    state["phase"] = "resolve_datasets"

    db = state["db"]
    config = state["config"]

    llm = get_LLM(
        base_url=config["llm"]["base_url"],
        model_name=config["llm"]["model_name"],
        temperature=0.01,
    )

    resolve_agent = build_agent(llm)

    cur = db.cursor()

    # -------------------------------------------------
    # 1. get new observations
    # -------------------------------------------------
    cur.execute("""
        SELECT id, title, description, confidence, doi
        FROM observations
        WHERE status = 'new'
    """)

    observations = cur.fetchall()

    matched = []
    new_datasets = []

    for obs_id, title, desc, confidence, doi in observations:

        if confidence < 0.75:
            update_observation_status(db, obs_id, 'ignored')
            continue

        obs_embedding = state["embedder"].encode(title + " " + (desc or ""))

        # -------------------------------------------------
        # 2. dataset candidate search
        # -------------------------------------------------
        cur.execute("""
            SELECT id, title, description, doi,
                   vec_distance_cosine(embedding_title_desc, ?) AS dist
            FROM datasets
            WHERE dist < 0.25
            ORDER BY dist ASC
            LIMIT 5
        """, (obs_embedding,))

        candidates = cur.fetchall()


        # -------------------------------------------------
        # 3. no dataset → create immediately (EMERGENT)
        # -------------------------------------------------
        if not candidates:
            dataset_id = create_dataset(db, obs_id)
            new_datasets.append(dataset_id)
            continue

        # -------------------------------------------------
        # 4. LLM verification
        # -------------------------------------------------
        is_matched = False
        for ds_id, ds_title, ds_desc, doi, dist in candidates:
            
            logger.info(f"Comparison: {title} vs {ds_title} - {dist}")

            messages = [
                SystemMessage(content=RESOLVE_SYSTEM),
                HumanMessage(content=f"""
OBSERVATION:
Title: {title}
Description: {desc}

DATASET:
Title: {ds_title}
Description: {ds_desc}
""")
            ]

            logger.info("⏳ Agent is thinking (resolve)...")
            result = resolve_agent.invoke({"messages": messages})

            try:
                decision = result["structured_response"]
                logger.info(f"Comparison: {title} vs {ds_title} = {decision.same_dataset} confidence: {decision.confidence}")

                if decision.same_dataset and decision.confidence > 0.85:

                    dataset_id = update_dataset_from_observation(db, ds_id, obs_id, state["embedder"])
                    matched.append((obs_id, ds_id))
                    is_matched = True
                    break

            except Exception as e:
                logger.error(f"Error resolving datasets: {e}")
                break

        if not is_matched:
            dataset_id = create_dataset(db, obs_id)
            new_datasets.append(dataset_id)

    if state["step_count"] < state["max_steps"]:
        state["step_count"] += 1
    else:
        state["rescrape_step_count"] += 1

    return {
        "phase": "resolve_datasets",
        "matched_dataset_ids": matched,
        "new_dataset_ids": new_datasets,
        "step_count": state["step_count"],
        "rescrape_step_count": state["rescrape_step_count"]
    }
