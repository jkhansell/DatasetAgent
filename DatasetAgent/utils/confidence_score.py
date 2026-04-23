def compute_observation_confidence(obs, evidence=None) -> float:
    """
    Confidence that an extracted observation is real, useful,
    and sufficiently identified.

    obs: Observation
    evidence: optional dict from scraper/page signals
    """

    score = 0.20  # base floor

    # -------------------------
    # Core fields
    # -------------------------
    if getattr(obs, "title", None):
        score += 0.22

    if getattr(obs, "description", None):
        score += 0.10

    if getattr(obs, "publisher", None):
        score += 0.12

    if getattr(obs, "license_", None):
        score += 0.10

    if getattr(obs, "doi", None):
        score += 0.18

    if getattr(obs, "keywords", None):
        if len(obs.keywords) > 0:
            score += 0.05

    # -------------------------
    # Entity type quality
    # -------------------------
    et = (getattr(obs, "entity_type", "") or "").lower()

    if et in {"dataset", "paper", "repository", "collection"}:
        score += 0.05

    # -------------------------
    # Evidence boosts
    # -------------------------
    if evidence:

        if evidence.get("jsonld"):
            score += 0.08

        if evidence.get("downloads"):
            score += 0.05

        if evidence.get("multi_page_support"):
            score += 0.08

        if evidence.get("title_exact_match"):
            score += 0.05

    # -------------------------
    # Penalties
    # -------------------------
    title = (getattr(obs, "title", "") or "").strip().lower()

    weak_titles = {
        "home", "homepage", "index",
        "dataset", "data portal",
        "untitled"
    }

    if title in weak_titles:
        score -= 0.18

    if len(title) < 4:
        score -= 0.12

    if not getattr(obs, "description", None) and not getattr(obs, "doi", None):
        score -= 0.10

    # -------------------------
    # Clamp
    # -------------------------
    score = max(0.01, min(score, 0.99))

    return round(score, 3)