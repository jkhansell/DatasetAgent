def compute_observation_confidence(obs) -> float:
    """
    Compute a confidence score for an observation based on available fields.
    """

    score = 0.0

    if obs.doi:
        score += 0.3
    if obs.title:
        score += 0.2
    if obs.description:
        score += 0.1
    if obs.license_:
        score += 0.15
    if obs.publisher:
        score += 0.1
    if obs.access_level:
        score += 0.1
    if obs.keywords:
        score += 0.05

    return min(score, 1.0)
