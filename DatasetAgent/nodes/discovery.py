import pprint
import uuid
import os
import sqlite3

from langchain_core.messages import HumanMessage, SystemMessage

from DatasetAgent.agents.discovery_agent import build_agent

from DatasetAgent.db.db import insert_search, insert_source


from DatasetAgent.utils.llm import get_LLM
from DatasetAgent.utils.logging import log_section
from DatasetAgent.utils.config import load_config
from DatasetAgent.utils.types import DatasetState
from DatasetAgent.utils.url import infer_source_type


from tavily import TavilyClient

tavily = TavilyClient()

def extract_domain(url: str) -> str:
    try:
        return url.split("/")[2].lower()
    except Exception:
        return ""


def discovery_node(state: DatasetState):
    log_section("NODE: DISCOVERY")
    state["phase"] = "discovery"

    config = state.config

    llm = get_LLM(
        base_url=config["llm"]["base_url"],
        model_name=config["llm"]["model_name"],
        temperature=0.4,
    )

    query_agent = build_agent(llm)

    # ==================================================
    # 1. Generate queries (single LLM call)
    # ==================================================
    messages = [
        SystemMessage(content=config["prompts"]["discovery"]),
        HumanMessage(
            content=config["prompts"]["discovery_human"].format(
                target_sources=state["target_sources"],
                dataset_goal=state["dataset_goal"]
            )
        )
    ]

    query_result = query_agent.invoke({"messages": messages})

    search_ids = []
    source_ids = []
    candidate_urls = set()

    # ==================================================
    # 2. For each generated query:
    #    save search -> Tavily search -> save sources
    # ==================================================
    if "structured_response" in query_result:

        for iid, entry in query_result["structured_response"].entries.items():

            # Save search lineage
            search_id = insert_search(
                state.db,
                query=entry.query,
                topic=entry.topic
            )
            search_ids.append(search_id)

            # Real search (deterministic, no second LLM)
            results = tavily.search(entry.query)

            for rank, r in enumerate(results.get("results", []), start=1):

                url = r.get("url")
                if not url:
                    continue

                source_id = insert_source(
                    db=state.db,
                    search_id=search_id,
                    url=url,
                    webdomain=extract_domain(url),
                    canonical_url=url,
                    title=r.get("title"),
                    description=r.get("content"),
                    tavily_score=r.get("score"),
                    rank_position=rank,
                    source_type=infer_source_type(url)
                )

                source_ids.append(source_id)
                candidate_urls.add(url)

    return {
        "search_ids": search_ids,
        "source_ids": source_ids,
        "candidate_urls": list(candidate_urls),
        "phase": "discovery"
    }