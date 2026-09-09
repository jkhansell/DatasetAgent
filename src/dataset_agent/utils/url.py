from urllib.parse import urlparse


def infer_source_type(url: str) -> str:
    """
    Infer the type of source based on URL.
    """

    domain = urlparse(url).netloc.lower()

    if "arxiv" in domain or "biorxiv" in domain or "medrxiv" in domain:
        return "preprint"
    elif "github" in domain:
        return "code"
    elif "zenodo" in domain or "figshare" in domain or "dataverse" in domain:
        return "dataset"
    elif "ncbi" in domain or "ebi" in domain or "ncbi.nlm.nih.gov" in domain:
        return "repository"
    elif "wikipedia" in domain:
        return "encyclopedia"
    else:
        return "web"
