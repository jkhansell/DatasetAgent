import json
import sqlite3
from typing import List, Dict

import numpy as np
from langchain_core.messages import SystemMessage, HumanMessage

from dataset_agent.agents.state import DatasetState
from dataset_agent.db.db import (
    insert_observation,
    create_dataset,
    update_dataset_from_observation,
    get_datasets,
)
from dataset_agent.utils.confidence_score import compute_observation_confidence
from dataset_agent.utils.logging import get_logger, log_section
from dataset_agent.utils.llm import get_LLM
from dataset_agent.agents.prompts import RESOLVE_DATASETS_SYSTEM

logger = get_logger(__name__)


def resolve_datasets_node(state: DatasetState):
    """
    Uses embedding similarity + LLM verification to match observations
    to existing datasets or create new ones.
    """

    log_section("NODE: RESOLVE_DATASETS")
    state["phase"] = "resolve_datasets"

    db = state["db"]
    config = state["config"]
    embedder = state["embedder"]

    datasets = get_datasets(db)
    if not datasets:
        logger.info("No datasets found to resolve against.")
        return {
            "matched_dataset_ids": [],
            "new_dataset_ids": [],
        }

    llm = get_LLM(
        base_url=config.get("llm", {}).get("base_url", ""),
        model_name=config.get("llm", {}).get("model_name", "gpt-4"),
        temperature=0.1,
    )

    matched_dataset_ids = []
    new_dataset_ids = []

    for obs_id in state.get("observation_ids", []):
        # Fetch observation
        cur = db.cursor()
        cur.execute("""
            SELECT id, title, description, doi, license_, publisher,
                   access_level, keywords, confidence, embedding_title_desc
            FROM observations
            WHERE id = ?
        """, (obs_id,))
        obs_row = cur.fetchone()
        if not obs_row:
            continue

        obs = type("Obs", (), {
            "id": obs_row["id"],
            "title": obs_row["title"],
            "description": obs_row["description"],
            "doi": obs_row["doi"],
            "license_": obs_row["license_"],
            "publisher": obs_row["publisher"],
            "access_level": obs_row["access_level"],
            "keywords": obs_row["keywords"],
            "confidence": obs_row["confidence"],
            "embedding_title_desc": np.frombuffer(obs_row["embedding_title_desc"], dtype=np.float32)
            if obs_row["embedding_title_desc"] else None,
        })()

        # ---- Step 1: Embedding similarity
        if obs.embedding_title_desc is None:
            obs.embedding_title_desc = embedder.encode(
                obs.title + "\n\n" + obs.description,
                prompt_name="Retrieval"
            )

        query_emb = obs.embedding_title_desc

        best_match = None
        best_sim = 0.0

        for ds in datasets:
            if not ds.get("embedding_title_desc"):
                continue

            ds_emb = np.frombuffer(ds["embedding_title_desc"], dtype=np.float32)
            sim = np.dot(query_emb, ds_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(ds_emb) + 1e-8
            )

            if sim > best_sim:
                best_sim = sim
                best_match = ds

        # ---- Step 2: LLM verification
        if best_match and best_sim > 0.75:
            logger.info(f"Observation {obs.id} matched dataset {best_match['id']} (similarity: {best_sim:.3f})")

            # Verify with LLM
            system_prompt = RESOLVE_DATASETS_SYSTEM
            human_prompt = f"""
Observation: {obs.title} - {obs.description}
Existing Dataset: {best_match['title']} - {best_match['description']}
Similarity: {best_sim:.3f}

Should these be merged into the same dataset? Answer with a single word: YES or NO.
"""
            try:
                result = llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ])
                response = result.content.strip().upper()
            except Exception as e:
                logger.error(f"LLM verification failed for observation {obs.id}: {e}")
                response = "YES"  # fallback to similarity decision

            if response == "YES":
                # Update dataset
                updated_id = update_dataset_from_observation(db, best_match["id"], obs.id, embedder)
                if updated_id:
                    matched_dataset_ids.append(updated_id)
                continue

        # ---- Step 3: Create new dataset
        new_id = create_dataset(db, obs.id)
        if new_id:
            new_dataset_ids.append(new_id)
            logger.info(f"Created new dataset {new_id} from observation {obs.id}")

    return {
        "matched_dataset_ids": matched_dataset_ids,
        "new_dataset_ids": new_dataset_ids,
    }
