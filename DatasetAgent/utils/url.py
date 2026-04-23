from urllib.parse import urlparse

def infer_source_type(url: str) -> str:
    """
    Fast heuristic source classifier from URL/domain/path only.
    Intended for discovery-time triage.
    """

    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path

    except Exception:
        return "unknown"

    full = f"{domain}{path}"

    # ==================================================
    # FILE TYPES
    # ==================================================
    if path.endswith(".pdf"):
        return "pdf"

    if path.endswith((".csv", ".tsv", ".parquet", ".feather")):
        return "data_file"

    if path.endswith((".zip", ".tar", ".gz", ".bz2", ".7z")):
        return "archive"

    if path.endswith((".json", ".xml", ".geojson", ".nc", ".h5", ".hdf5")):
        return "structured_data"

    if path.endswith((".shp", ".gpkg", ".tif", ".tiff")):
        return "geospatial_data"

    # ==================================================
    # CODE / REPOSITORIES
    # ==================================================
    if "github.com" in domain:
        return "repository"

    if "gitlab.com" in domain:
        return "repository"

    if "bitbucket.org" in domain:
        return "repository"

    if "huggingface.co" in domain:
        if "/datasets/" in path:
            return "dataset_portal"
        return "model_repository"

    # ==================================================
    # DATASET PORTALS / REPOSITORIES
    # ==================================================
    dataset_domains = [
        "kaggle.com",
        "zenodo.org",
        "figshare.com",
        "dataverse.org",
        "data.world",
        "opendata.arcgis.com",
        "registry.opendata.aws",
        "data.gov",
        "data.europa.eu",
        "datahub.io",
        "mendeley.com",
        "dryad",
        "openml.org",
        "physionet.org",
    ]

    if any(d in domain for d in dataset_domains):
        return "dataset_portal"

    # ==================================================
    # PAPERS / PUBLICATIONS
    # ==================================================
    paper_domains = [
        "arxiv.org",
        "doi.org",
        "acm.org",
        "ieee.org",
        "springer.com",
        "nature.com",
        "sciencedirect.com",
        "wiley.com",
        "mdpi.com",
        "researchgate.net",
        "semanticscholar.org",
        "paperswithcode.com",
        "jmlr.org",
        "plos.org",
    ]

    if any(d in domain for d in paper_domains):
        return "paper"

    # ==================================================
    # CLOUD STORAGE / DIRECT DOWNLOADS
    # ==================================================
    storage_domains = [
        "drive.google.com",
        "dropbox.com",
        "mega.nz",
        "s3.amazonaws.com",
        "blob.core.windows.net",
        "storage.googleapis.com",
    ]

    if any(d in domain for d in storage_domains):
        return "download_host"

    # ==================================================
    # DOCS / API / SOFTWARE
    # ==================================================
    if any(x in path for x in ["/docs", "/documentation", "/guide"]):
        return "documentation"

    if any(x in path for x in ["/api", "/swagger", "/openapi"]):
        return "api"

    # ==================================================
    # UNIVERSITY / GOVERNMENT / LABS
    # ==================================================
    if domain.endswith(".gov"):
        return "government_data"

    if domain.endswith(".edu"):
        return "academic_site"

    if domain.endswith(".ac.uk"):
        return "academic_site"

    if domain.endswith(".org"):
        if "open" in domain or "data" in domain:
            return "organization_data"

    # ==================================================
    # NEWS / BLOGS / ARTICLES
    # ==================================================
    news_domains = [
        "medium.com",
        "substack.com",
        "towardsdatascience.com",
        "analyticsvidhya.com",
        "blogspot.com",
        "wordpress.com",
    ]

    if any(d in domain for d in news_domains):
        return "blog"

    # ==================================================
    # PATH HINTS
    # ==================================================
    if any(x in path for x in ["/dataset", "/datasets", "/data"]):
        return "dataset_page"

    if any(x in path for x in ["/paper", "/publication", "/publications"]):
        return "paper"

    if any(x in path for x in ["/download", "/files"]):
        return "download_page"

    if any(x in path for x in ["/benchmark", "/leaderboard"]):
        return "benchmark_page"

    # ==================================================
    # FALLBACKS
    # ==================================================
    if domain:
        return "html_page"

    return "unknown"