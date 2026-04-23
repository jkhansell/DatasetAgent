import os
import sqlite3
import sqlite_vec

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
,
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

        date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

        paper_url TEXT,
        code_url TEXT,

        potential_download_urls TEXT,

        embedding_title FLOAT[{dim}] CHECK(
            typeof(embedding_title) = 'blob'
            AND vec_length(embedding_title) = {dim}
        ),

        embedding_description FLOAT[{dim}] CHECK(
            typeof(embedding_description) = 'blob'
            AND vec_length(embedding_description) = {dim}
        )
    );

    CREATE INDEX IF NOT EXISTS idx_datasets_title
    ON datasets(title);

    CREATE INDEX IF NOT EXISTS idx_datasets_doi
    ON datasets(doi);

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

        embedding_title FLOAT[{dim}] CHECK(
            typeof(embedding_title) = 'blob'
            AND vec_length(embedding_title) = {dim}
        ),

        embedding_description FLOAT[{dim}] CHECK(
            typeof(embedding_description) = 'blob'
            AND vec_length(embedding_description) = {dim}
        ),

        FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
        FOREIGN KEY(matched_dataset) REFERENCES datasets(id)
    );

    CREATE INDEX IF NOT EXISTS idx_obs_source
    ON observations(source_id);

    CREATE INDEX IF NOT EXISTS idx_obs_dataset
    ON observations(matched_dataset);

    CREATE INDEX IF NOT EXISTS idx_obs_status
    ON observations(status);
    """)

    db.commit()
    db.close()

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
            topic,
        )
        VALUES (?, ?)
    """, (
        query,
        topic,
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


def insert_dataset(
    db,
    title: str,
    description: str = None,
    doi: str = None,
    license_: str = None,
    paper_url: str = None,
    code_url: str = None,
    potential_download_urls: str = None,
    embedding_title = None,
    embedding_description = None
) -> int:
    cur = db.cursor()

    cur.execute("""
        INSERT INTO datasets (
            title,
            description,
            doi,
            license_,
            paper_url,
            code_url,
            potential_download_urls,
            embedding_title,
            embedding_description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        description,
        doi,
        license_,
        paper_url,
        code_url,
        potential_download_urls,
        embedding_title,
        embedding_description
    ))

    db.commit()

    return cur.lastrowid


def insert_observation(
    db,
    source_id: int,
    entity_type: str,
    title: str,
    description: str = None,
    license_: str = None,
    doi: str = None,
    matched_dataset: int = None,
    confidence: float = 0.0,
    status: str = "new",
    embedding_title = None,
    embedding_description = None
) -> int:
    cur = db.cursor()

    cur.execute("""
        INSERT INTO observations (
            source_id,
            matched_dataset,
            entity_type,
            title,
            description,
            license_,
            doi,
            confidence,
            status,
            embedding_title,
            embedding_description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source_id,
        matched_dataset,
        entity_type,
        title,
        description,
        license_,
        doi,
        confidence,
        status,
        embedding_title,
        embedding_description
    ))

    db.commit()

    return cur.lastrowid

# =====================================================
# READ FUNCTIONS
# =====================================================

def get_sources(
    db,
    urls_only: bool = True,
    limit: int = 25,
    only_pending: bool = True
) -> list:
    """
    Retrieve sources for crawl/extract pipeline.
    """

    cur = db.cursor()

    where = []
    params = []

    if only_pending:
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

# =====================================================
# EXAMPLE USAGE
# =====================================================

if __name__ == "__main__":
    init_db()
    print("Database initialized.")