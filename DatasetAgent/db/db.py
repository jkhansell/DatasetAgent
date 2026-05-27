import os
import sqlite3
import sqlite_vec
import numpy as np
from urllib.parse import urlparse, urlunparse
from DatasetAgent.utils.logging import get_logger

logger = get_logger(__name__)

DB_PATH = "data/datasets.db"

# =====================================================
# CONNECTION
# =====================================================

def load_db(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    db.execute("PRAGMA foreign_keys = ON;")
    db.execute("PRAGMA journal_mode = WAL;")
    db.execute("PRAGMA synchronous = NORMAL;")

    return db


def save_db(db: sqlite3.Connection):
    db.commit()
    db.close()


# =====================================================
# INIT DATABASE
# =====================================================

def init_db(path: str = DB_PATH, dim: int = 768):
    db = load_db(path)
    cur = db.cursor()

    cur.executescript(f"""
    -- ==================================================
    -- SEARCHES (one Tavily/API discovery event)
    -- ==================================================
    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        query TEXT NOT NULL,
        topic TEXT,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_searches_query
    ON searches(query);

    -- ==================================================
    -- SOURCES (returned URLs / discovered pages)
    -- ==================================================
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        search_id INTEGER,

        url TEXT UNIQUE NOT NULL,
        webdomain TEXT,
        canonical_url TEXT,

        title TEXT,
        description TEXT,

        tavily_score REAL,
        rank_position INTEGER,

        source_type TEXT,

        processed INTEGER DEFAULT 0,
        crawl_status TEXT DEFAULT 'new',

        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(search_id) REFERENCES searches(id)
    );

    CREATE INDEX IF NOT EXISTS idx_sources_url
    ON sources(url);

    CREATE INDEX IF NOT EXISTS idx_sources_domain
    ON sources(webdomain);

    CREATE INDEX IF NOT EXISTS idx_sources_search
    ON sources(search_id);

    -- ==================================================
    -- DATASETS (canonical memory)
    -- ==================================================
    CREATE TABLE IF NOT EXISTS datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        title TEXT NOT NULL,
        description TEXT,

        doi TEXT,
        license_ TEXT,
        publisher TEXT,
        access_level TEXT,
        keywords TEXT,

        date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

        paper_url TEXT,
        code_url TEXT,
        dataset_url TEXT,

        potential_download_urls TEXT,

        embedding_title_desc FLOAT[{dim}] CHECK(
            typeof(embedding_title_desc) = 'blob'
            AND vec_length(embedding_title_desc) = {dim}
        )
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_datasets_title
    ON datasets(title) WHERE title IS NOT NULL;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_datasets_doi
    ON datasets(doi) WHERE doi IS NOT NULL;

    -- ==================================================
    -- OBSERVATIONS (runtime extracted entities)
    -- ==================================================
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        source_id INTEGER NOT NULL,
        matched_dataset INTEGER,

        entity_type TEXT,
        title TEXT,
        description TEXT,

        license_ TEXT,
        doi TEXT,
        publisher TEXT,
        access_level TEXT,
        keywords TEXT,

        confidence REAL DEFAULT 0.0,
        status TEXT DEFAULT 'new',

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        embedding_title_desc FLOAT[{dim}] CHECK(
            typeof(embedding_title_desc) = 'blob'
            AND vec_length(embedding_title_desc) = {dim}
        ),

        FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
        FOREIGN KEY(matched_dataset) REFERENCES datasets(id)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_unique_doi
    ON observations(doi)
    WHERE doi IS NOT NULL;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_unique_title
    ON observations(title);

    CREATE INDEX IF NOT EXISTS idx_obs_source
    ON observations(source_id);

    CREATE INDEX IF NOT EXISTS idx_obs_dataset
    ON observations(matched_dataset);

    CREATE INDEX IF NOT EXISTS idx_obs_status
    ON observations(status);
    
    """)

    db.commit()

    return db

# =====================================================
# WRITE FUNCTIONS
# =====================================================

def insert_search(
    db,
    query: str,
    topic: str = None,
) -> int:
    cur = db.cursor()

    cur.execute("""
        INSERT INTO searches (
            query,
            topic
        )
        VALUES (?, ?)
    """, (
        query,
        topic
    ))

    db.commit()
    return cur.lastrowid


def insert_source(
    db,
    url: str,
    search_id: int = None,
    webdomain: str = None,
    canonical_url: str = None,
    title: str = None,
    description: str = None,
    tavily_score: float = None,
    rank_position: int = None,
    source_type: str = None,
    processed: int = 0,
    crawl_status: str = "new"
) -> int:
    """
    Insert source if unseen.
    Returns id.
    """
    
    if url:
        parsed = urlparse(url)
        url = urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), parsed.params, parsed.query, ''))

    cur = db.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO sources (
            search_id,
            url,
            webdomain,
            canonical_url,
            title,
            description,
            tavily_score,
            rank_position,
            source_type,
            processed,
            crawl_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        search_id,
        url,
        webdomain,
        canonical_url,
        title,
        description,
        tavily_score,
        rank_position,
        source_type,
        processed,
        crawl_status
    ))

    db.commit()

    cur.execute(
        "SELECT id FROM sources WHERE url = ?",
        (url,)
    )

    return cur.fetchone()["id"]

def update_source_status(db, source_id: int, processed: int, crawl_status: str):
    cur = db.cursor()
    cur.execute("""
        UPDATE sources
        SET processed = ?, crawl_status = ?
        WHERE id = ?
    """, (processed, crawl_status, source_id))
    db.commit()

def update_observation_status(db, obs_id: int, status: str):
    cur = db.cursor()
    cur.execute("""
        UPDATE observations
        SET status = ?
        WHERE id = ?
    """, (status, obs_id))
    db.commit()

def insert_observation(
    db,
    source_id: int,
    entity_type: str,
    title: str,
    description: str = None,
    license_: str = None,
    doi: str = None,
    publisher: str = None,
    access_level: str = None,
    keywords: str = None,
    matched_dataset: int = None,
    confidence: float = 0.0,
    status: str = "new",
    embedding_title_desc = None,
) -> int:
    cur = db.cursor()

    cur.execute("SELECT id FROM observations WHERE source_id = ? AND LOWER(title) = LOWER(?)", (source_id, title))
    existing = cur.fetchone()
    if existing:
        return existing["id"]

    cur.execute("""
        INSERT INTO observations (
            source_id,
            matched_dataset,
            entity_type,
            title,
            description,
            license_,
            doi,
            publisher,
            access_level,
            keywords,
            confidence,
            status,
            embedding_title_desc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source_id,
        matched_dataset,
        entity_type,
        title,
        description,
        license_,
        doi,
        publisher,
        access_level,
        keywords,
        confidence,
        status,
        embedding_title_desc
    ))

    db.commit()

    return cur.lastrowid

def create_dataset(db, obs_id):
    """
    Create a new dataset from a single observation
    (seed step for emergent dataset formation).
    """

    cur = db.cursor()

    # -------------------------------------------------
    # 1. Fetch observation
    # -------------------------------------------------
    cur.execute("""
        SELECT title, description, doi, license_, publisher,
               access_level, keywords, embedding_title_desc
        FROM observations
        WHERE id = ?
    """, (obs_id,))

    row = cur.fetchone()

    if not row:
        return None

    title, desc, doi, license_, publisher, access_level, keywords, emb = row

    existing = None
    if doi:
        cur.execute("SELECT id FROM datasets WHERE doi = ?", (doi,))
        existing = cur.fetchone()
        
    if not existing:
        cur.execute("SELECT id FROM datasets WHERE LOWER(title) = LOWER(?)", (title,))
        existing = cur.fetchone()
    
    if existing:
        dataset_id = existing["id"]
    else:
        # -------------------------------------------------
        # 2. Create dataset (seeded from observation)
        # -------------------------------------------------
        cur.execute("""
            INSERT INTO datasets (
                title,
                description,
                doi,
                license_,
                publisher,
                access_level,
                keywords,
                embedding_title_desc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            desc,
            doi,
            license_,
            publisher,
            access_level,
            keywords,
            emb
        ))
    
        dataset_id = cur.lastrowid

    # -------------------------------------------------
    # 3. Attach observation
    # -------------------------------------------------
    cur.execute("""
        UPDATE observations
        SET matched_dataset = ?, status = 'resolved'
        WHERE id = ?
    """, (dataset_id, obs_id))

    db.commit()

    return dataset_id

def merge_text(old, new):
    if not old:
        return new
    if not new:
        return old
    if new in old:
        return old
    return old + "\n" + new

def merge_keywords(old, new):
    old_set = set((old or "").split("|")) if old else set()
    new_set = set(new or [])

    return "|".join(sorted(old_set | new_set))

def merge_url(old, new):
    if not old:
        return new
    if not new:
        return old

    urls = set(old.split("|"))
    urls.add(new)

    return "|".join(urls)

def update_centroid(old_blob, new_array, alpha=0.2, conf=1.0):
    if old_blob is None:
        return new_array
    
    old_array = np.frombuffer(old_blob, dtype=np.float32)
    updated = (1 - alpha) * old_array + alpha * new_array * conf
    return updated.astype(np.float32).tobytes()

def update_dataset_from_observation(db, dataset_id, obs_id, embedder):
    """
    Enrich an existing dataset using a new observation.
    """

    cur = db.cursor()

    # -------------------------------------------------
    # 0. Fetch observation (MISSING in your version)
    # -------------------------------------------------
    cur.execute("""
        SELECT title, description, doi, license_, publisher,
               access_level, keywords, embedding_title_desc
        FROM observations
        WHERE id = ?
    """, (obs_id,))

    obs_row = cur.fetchone()

    if not obs_row:
        return None

    (obs_title, obs_desc, obs_doi, obs_license,
     obs_publisher, obs_access, obs_keywords, obs_emb) = obs_row

    obs = type("Obs", (), {})()  # lightweight object
    obs.title = obs_title
    obs.description = obs_desc
    obs.doi = obs_doi
    obs.license_ = obs_license
    obs.publisher = obs_publisher
    obs.access_level = obs_access
    obs.keywords = obs_keywords
    obs.embedding_title_desc = obs_emb

    # -------------------------------------------------
    # 1. Fetch dataset state
    # -------------------------------------------------
    cur.execute("""
        SELECT title, description, doi, license_, publisher,
               access_level, keywords, embedding_title_desc,
               paper_url, code_url, dataset_url
        FROM datasets
        WHERE id = ?
    """, (dataset_id,))

    ds = cur.fetchone()

    if not ds:
        return None

    (title, desc, doi, license_, publisher,
     access_level, keywords, emb,
     paper_url, code_url, dataset_url) = ds

    # -------------------------------------------------
    # 2. Field-level enrichment
    # -------------------------------------------------
    new_title = title or obs.title
    new_desc = merge_text(desc, obs.description)

    new_doi = doi or obs.doi
    new_license = license_ or obs.license_
    new_publisher = publisher or obs.publisher
    new_access = access_level or obs.access_level

    new_keywords = merge_keywords(keywords, obs.keywords)

    new_paper_url = paper_url
    new_code_url = code_url
    new_dataset_url = dataset_url

    # -------------------------------------------------
    # 3. Embedding update (centroid)
    # -------------------------------------------------
    new_emb = update_centroid(emb, np.frombuffer(obs.embedding_title_desc, dtype=np.float32))

    # -------------------------------------------------
    # 4. Persist update
    # -------------------------------------------------
    cur.execute("""
        UPDATE datasets
        SET title = ?,
            description = ?,
            doi = ?,
            license_ = ?,
            publisher = ?,
            access_level = ?,
            keywords = ?,
            paper_url = ?,
            code_url = ?,
            dataset_url = ?,
            embedding_title_desc = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        new_title,
        new_desc,
        new_doi,
        new_license,
        new_publisher,
        new_access,
        new_keywords,
        new_paper_url,
        new_code_url,
        new_dataset_url,
        new_emb,
        dataset_id
    ))

    # -------------------------------------------------
    # 5. Attach observation
    # -------------------------------------------------
    cur.execute("""
        UPDATE observations
        SET matched_dataset = ?, status = 'resolved'
        WHERE id = ?
    """, (dataset_id, obs_id))

    db.commit()

    return dataset_id


# =====================================================
# READ FUNCTIONS
# =====================================================

def get_sources(
    db,
    urls_only: bool = True,
    limit: int = 25,
    only_pending: bool = True,
    for_rescrape: bool = False
) -> list:
    """
    Retrieve sources for crawl/extract pipeline.
    """

    cur = db.cursor()

    where = []
    params = []

    if for_rescrape:
        where.append("processed = 1")
        where.append("crawl_status = 'scraped'")
    elif only_pending:
        where.append("processed = 0")
        where.append("crawl_status IN ('new', 'retry')")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    if urls_only:
        query = f"""
        SELECT url
        FROM sources
        {where_sql}
        ORDER BY rank_position ASC, tavily_score DESC, id ASC
        LIMIT ?
        """
    else:
        query = f"""
        SELECT
            id,
            search_id,
            url,
            webdomain,
            canonical_url,
            title,
            description,
            tavily_score,
            rank_position,
            source_type,
            processed,
            crawl_status,
            timestamp
        FROM sources
        {where_sql}
        ORDER BY rank_position ASC, tavily_score DESC, id ASC
        LIMIT ?
        """

    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()

    if urls_only:
        return [r[0] for r in rows]

    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]

def get_observations(db, doi=None, title=None, limit=None):
    """
    Flexible observation fetch:
    - by DOI
    - by title
    - or bulk (for similarity scan)
    """

    cur = db.cursor()

    # ---- Case 1: DOI lookup
    if doi is not None:
        cur.execute("""
            SELECT *
            FROM observations
            WHERE doi = ?
            LIMIT 1
        """, (doi,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ---- Case 2: Title lookup
    if title is not None:
        cur.execute("""
            SELECT *
            FROM observations
            WHERE title = ?
            LIMIT 1
        """, (title,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ---- Case 3: Bulk fetch (for embedding similarity)
    query = "SELECT * FROM observations ORDER BY created_at DESC"
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    rows = cur.fetchall()

    results = []
    for r in rows:
        d = dict(r)

        # ---- IMPORTANT: convert embedding from blob → numpy
        if d.get("embedding_title_desc") is not None:
            d["embedding_title_desc"] = np.frombuffer(
                d["embedding_title_desc"], dtype=np.float32
            )

        results.append(d)

    return results

def get_datasets(db) -> list:
    """
    Retrieve all recorded datasets.
    """
    cur = db.cursor()
    cur.execute("""
        SELECT
            id,
            title,
            description,
            doi,
            license_,
            publisher,
            access_level,
            keywords,
            paper_url,
            code_url,
            dataset_url
        FROM datasets
    """)
    rows = cur.fetchall()
    
    # Check if empty
    if not rows:
        return []

    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]

# =====================================================
# EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":
    init_db()
    logger.info("✅ Database initialized.")