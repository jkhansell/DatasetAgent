import numpy as np

from langchain_core.messages import HumanMessage, SystemMessage

from DatasetAgent.agents.crawl_agent import build_agent 
from DatasetAgent.agents.prompts import CRAWL_EXTRACT_SYSTEM, RESCRAPE_SYSTEM, RESCRAPE_HUMAN
from DatasetAgent.agents.state import DatasetState



from DatasetAgent.utils.logging import log_section, get_logger
from DatasetAgent.utils.llm import get_LLM
from DatasetAgent.utils.confidence_score import compute_observation_confidence

logger = get_logger(__name__)

from DatasetAgent.db.db import get_sources, insert_observation, get_datasets, update_source_status, get_observations  # <-- add this
from numpy.linalg import norm

def is_duplicate_observation(db, embedder, title, desc, doi, threshold=0.92):
    """
    Hybrid duplicate detection:
    1. DOI exact match
    2. Title exact match
    3. Embedding cosine similarity
    """

    # ---- 1. DOI check (strongest signal)
    if doi:
        existing = get_observations(db, doi=doi)
        if existing:
            return True

    # ---- 2. Title exact match
    if title:
        existing = get_observations(db, title=title)
        if existing:
            return True

    # ---- 3. Embedding similarity
    query_emb = embedder.encode(title + "\n\n" + desc, prompt_name="Retrieval")

    candidates = get_observations(db, limit=200)  # keep bounded
    for obs in candidates:
        emb = obs.get("embedding_title_desc")
        if emb is None:
            continue

        sim = np.dot(query_emb, emb) / (norm(query_emb) * norm(emb) + 1e-8)

        if sim > threshold:
            return True

    return False

def crawl_extract_node(state: DatasetState):
    """
    Agentic crawl/extract node with hardcoded prompts.
    """

    log_section("NODE: CRAWL_EXTRACT")
    state["phase"] = "crawl_extract"

    config = state["config"]

    llm = get_LLM(
        base_url=config["llm"]["base_url"],
        model_name=config["llm"]["model_name"],
        temperature=0.05,
    )

    crawl_agent = build_agent(llm)

    db = state["db"]
    embedder = state["embedder"]

    target_datasets = config.get("target_datasets", 10)
    current_datasets = len(get_datasets(db))

    if current_datasets >= target_datasets:
        logger.info(f"Target datasets reached ({current_datasets}/{target_datasets}). Skipping crawl/extract.")
        return {
            "phase": "crawl_extract",
            "source_ids": [],
            "observation_ids": [],
        }

    is_rescrape = state["step_count"] >= state["max_steps"]
    
    sources = get_sources(
        db,
        urls_only=False,
        limit=state["target_sources"],
        only_pending=not is_rescrape,
        for_rescrape=is_rescrape
    )

    inserted = []
    processed = []

    for i, src in enumerate(sources):
        logger.info(f"🌐 Processing source {i+1}/{len(sources)}")

        source_id = src["id"]
        url = src["url"]

        if is_rescrape:
            human_prompt = RESCRAPE_HUMAN.format(
                url=url,
                db_string="title, description, doi, license_, publisher, access_level, keywords, matched_dataset",
                scraped_text="(Text provided by tools)"
            )
        else:
            human_prompt = f"""
Investigate this source:

{url}

Use tools to explore only useful pages.
Identify datasets, papers, repositories, portals, or collections.
Return structured ObservationOutput.
"""

        sys_prompt = RESCRAPE_SYSTEM if is_rescrape else CRAWL_EXTRACT_SYSTEM

        try:
            logger.info("⏳ Agent is thinking (crawl/extract)...")
            result = crawl_agent.invoke({
                "messages": [
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=human_prompt),
                ]
            })

            if "structured_response" not in result:
                processed.append(source_id)
                update_source_status(db, source_id, processed=1, crawl_status="rescraped" if is_rescrape else "scraped")
                continue

            obs = result["structured_response"]

            title = obs.title or ""
            desc = obs.description or ""

            # ---- DUPLICATE CHECK (ADD THIS BLOCK)
            if is_duplicate_observation(
                db=db,
                embedder=embedder,
                title=title,
                desc=desc,
                doi=obs.doi
            ):
                logger.info("⚠️ Skipping duplicate observation")
                processed.append(source_id)
                update_source_status(db, source_id, processed=1, crawl_status="rescraped" if is_rescrape else "scraped")
                continue

            # ---- EMBEDDING AFTER PASS
            emb_title_desc = embedder.encode(title + "\n\n" + desc, prompt_name="Retrieval")

            obs_id = insert_observation(
                db=db,
                source_id=source_id,
                entity_type=obs.entity_type,
                title=obs.title,
                description=obs.description,
                license_=obs.license_,
                doi=obs.doi,
                publisher=obs.publisher,
                access_level=obs.access_level,
                keywords="|".join(obs.keywords),
                embedding_title_desc=emb_title_desc.astype(np.float32),
                confidence=compute_observation_confidence(obs),
                status="new"
            )

            inserted.append(obs_id)
            processed.append(source_id)
            update_source_status(db, source_id, processed=1, crawl_status="rescraped" if is_rescrape else "scraped")

        except Exception as e:
            logger.error(f"Error during crawl/extract: {e}")
            pass

    return {
        "phase": "crawl_extract",
        "source_ids": processed,
        "observation_ids": inserted,
    }