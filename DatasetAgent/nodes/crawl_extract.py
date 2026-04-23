from langchain_core.messages import HumanMessage, SystemMessage

from DatasetAgent.agents.crawl_agent import build_agent 
from DatasetAgent.agents.state import State

from DatasetAgent.utils.logging import log_section
from DatasetAgent.utils.types import DatasetState
from DatasetAgent.utils.llm import get_LLM
from DatasetAgent.utils.confidence_score import compute_observation_confidence


from DatasetAgent.db.db import get_sources, insert_observation, mark_source_processed, mark_source_error

def crawl_extract_node(state: DatasetState):
    """
    Agentic crawl/extract node with hardcoded prompts.
    """

    log_section("NODE: CRAWL_EXTRACT")
    state["phase"] = "crawl_extract"

    config = state.config

    llm = get_LLM(
        base_url=config["llm"]["base_url"],
        model_name=config["llm"]["model_name"],
        temperature=0.05,
    )

    crawl_agent = build_agent(llm)

    db = state.db
    embedder = state.embedder

    sources = get_sources(
        db,
        urls_only=False,
        limit=25,
        only_pending=True
    )

    inserted = []
    processed = []

    system_prompt = """
You are a dataset discovery analyst.

Your task is to investigate a target website using available tools.

Use scraping tools selectively to inspect relevant pages such as:
- homepage
- datasets/catalog pages
- download/resource pages
- about/license pages
- publication pages

Extract all distinct relevant entities and return only structured ObservationOutput.

Rules:
- Prefer precision over speculation.
- Merge duplicates.
- Use null when unknown.
- Keep keywords concise.
"""

    for src in sources:

        source_id = src["id"]
        url = src["url"]

        human_prompt = f"""
Investigate this source:

{url}

Use tools to explore only useful pages.
Identify datasets, papers, repositories, portals, or collections.
Return structured ObservationOutput.
"""

        try:
            result = crawl_agent.invoke({
                "messages": [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ]
            })

            if "structured_response" not in result:
                mark_source_processed(db, source_id)
                processed.append(source_id)
                continue

            structured = result["structured_response"]

            for _, obs in structured.entries.items():

                title = obs.title or ""
                desc = obs.description or ""

                emb_title = embedder.encode(title)
                emb_desc = embedder.encode(desc)

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
                    embedding_title=emb_title,
                    embedding_description=emb_desc,
                    confidence=compute_observation_confidence(obs),
                    status="new"
                )

                inserted.append(obs_id)
            processed.append(source_id)

        except Exception as e:
            print(e)
            pass

    return {
        "phase": "crawl_extract",
        "source_ids": processed,
        "observation_ids": inserted,
    }