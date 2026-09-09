import json
import math
import os
import pprint
import sqlite3
import uuid
from langchain_core.messages import HumanMessage, SystemMessage
from SPARQLWrapper import SPARQLWrapper, JSON

from dataset_agent.agents.discovery_agent import build_agent
from dataset_agent.agents.prompts import DISCOVERY_SYSTEM
from dataset_agent.agents.state import DatasetState
from dataset_agent.db.db import get_sources, insert_search, insert_source
from dataset_agent.utils.llm import get_LLM
from dataset_agent.utils.logging import get_logger, log_section
from dataset_agent.utils.url import infer_source_type

logger = get_logger(__name__)

from tavily import TavilyClient

tavily = TavilyClient()

def _cache_key_for_qids(qids: list[str]) -> str:
    """Derive a deterministic cache filename from a list of Wikidata QIDs."""
    safe_qids = "".join(q.replace("Q", "") for q in qids)
    return f"wikidata_ontology_{safe_qids}.json"


def fetch_wikidata_ontology(
    qids: list[str],
    cache_file: str | None = None,
    user_agent: str = "DatasetAgent/1.0",
) -> list[dict]:
    """
    Fetch the full P279 (subclass of) ontology hierarchy for a list of
    Wikidata QIDs, caching the result locally to avoid repeated queries.

    Parameters
    ----------
    qids : list[str]
        Wikidata entity IDs to root the hierarchy search under
        (e.g. ``["Q42395"]`` for leukocytes, or any other set).
    cache_file : str, optional
        Path to the local JSON cache.  Defaults to a name derived from
        ``qids`` such as ``wikidata_ontology_42395.json``.
    user_agent : str
        User-Agent header sent to Wikidata's SPARQL endpoint.

    Returns
    -------
    list[dict]
        A list of ``{"child_label": ..., "parent_label": ...}`` pairs
        representing the ontology hierarchy.
    """
    if cache_file is None:
        cache_file = _cache_key_for_qids(qids)

    # --- cache hit ---------------------------------------------------------
    if os.path.exists(cache_file):
        logger.info(f"Loading ontology from local cache: {cache_file}")
        with open(cache_file, "r") as f:
            return json.load(f)

    # --- cache miss: query Wikidata ----------------------------------------
    qids_str = ", ".join(f"wd:{q}" for q in qids)
    logger.info(f"Cache miss. Querying Wikidata for ontology rooted at {qids_str}...")

    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.agent = user_agent

    # Build a disjunctive query: one subtree per QID
    qid_conditions = " | ".join(f"?cell wdt:P279* {q}" for q in qids)
    query = f"""
    SELECT DISTINCT ?cellLabel ?parentLabel WHERE {{
      {{
        {qid_conditions} .
        ?cell wdt:P279 ?parent .
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        ontology_pairs: list[dict] = []

        for result in results["results"]["bindings"]:
            child = result["cellLabel"]["value"]
            parent = result["parentLabel"]["value"]

            # Skip non-human (mouse) and raw Q-IDs that slipped through
            if (
                not child.startswith("Q")
                and not parent.startswith("Q")
                and "mouse" not in child.lower()
                and "mouse" not in parent.lower()
            ):
                ontology_pairs.append({
                    "child_label": child,
                    "parent_label": parent,
                })

        # Save cache to file
        with open(cache_file, "w") as f:
            json.dump(ontology_pairs, f, indent=4)
        logger.info(f"Successfully cached {len(ontology_pairs)} concepts to {cache_file}")

        return ontology_pairs

    except Exception as e:
        logger.error(f"Error fetching from Wikidata: {e}")
        # Return empty list so the pipeline never stalls completely
        return []

def fetch_leukocyte_ontology() -> list[dict]:
    """
    Backwards-compatible wrapper: fetch leukocyte ontology (Q42395).

    Prefer ``fetch_wikidata_ontology`` for new code so you can pass
    arbitrary QIDs.
    """
    return fetch_wikidata_ontology(
        qids=["Q42395"],
        user_agent="LeukoCoDatasetCurator/1.0 (mailto:your_email@example.com)",
    )


def extract_domain(url: str) -> str:
    try:
        return url.split("/")[2].lower()
    except Exception:
        return ""

def discovery_node(state: DatasetState):
    log_section("NODE: DISCOVERY")
    state["phase"] = "discovery"

    sources = get_sources(
        state["db"],
        urls_only=True,
        limit=state["target_sources"],
        only_pending=False
    )

    if len(sources) >= state["target_sources"]:
        logger.info("Target sources reached")
        return {
            "phase": "discovery"
        }

    config = state["config"]

    # ==================================================
    # 0. Load Ontology Cache
    # ==================================================
    wikidata_qids = config.get("wikidata_qids", ["Q42395"])
    ontology_nodes = fetch_wikidata_ontology(qids=wikidata_qids)

    # Flatten unique concepts out to pass into your system instructions
    unique_concepts = list(set([node["child_label"] for node in ontology_nodes] + [node["parent_label"] for node in ontology_nodes]))

    llm = get_LLM(
        base_url=config["llm"]["base_url"],
        model_name=config["llm"]["model_name"],
        temperature=0.4,
    )

    query_agent = build_agent(llm)

    # ==================================================
    # 1. Generate queries (single LLM call)
    # ==================================================
    existing_urls = get_sources(state["db"], urls_only=True, limit=1000, only_pending=False)

    # Inject both existing URLs and our explicit, structural ontology terms
    system_prompt = DISCOVERY_SYSTEM.format(
        urls="\n".join(existing_urls),
        candidate_urls="\n".join(state.get("candidate_urls", []))
    )

    # Append the structural guide directly to the system prompt context
    system_prompt += f"\n\nAvailable Target Ontology Knowledge Base Concepts:\n" + ", ".join(unique_concepts[:150]) # Capped variant safe for contexts

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=config["prompts"]["discovery_human"].format(
                target_sources=state["target_sources"],
                dataset_goal=state["dataset_goal"],
            )
        )
    ]

    logger.info("Agent is thinking (discovery)...")
    query_result = query_agent.invoke({"messages": messages})

    search_ids = []
    source_ids = []
    candidate_urls = set()

    # ==================================================
    # 2. Process Queries
    # ==================================================
    if "structured_response" in query_result:
        for iid, entry in query_result["structured_response"].entries.items():

            search_id = insert_search(
                state["db"],
                query=entry.query,
                topic=entry.topic
            )
            search_ids.append(search_id)

            results = tavily.search(entry.query)

            for rank, r in enumerate(results.get("results", []), start=1):
                url = r.get("url")
                if not url:
                    continue

                source_id = insert_source(
                    db=state["db"],
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
        "current_sources": len(sources),
        "phase": "discovery"
    }
