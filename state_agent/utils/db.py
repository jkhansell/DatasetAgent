import sqlite3
import os
from .models import DatasetEntry

DB_PATH = "./data/datasets.db"

db_string = """
    iid TEXT PRIMARY KEY,
    url TEXT,
    potential_urls TEXT,
    title TEXT,
    description TEXT,
    repository TEXT,
    task TEXT,
    annotation_type TEXT,
    source TEXT,
    license TEXT,
    point_of_contact TEXT,
    contact_email TEXT,
    number_images INTEGER,
    dimensions TEXT,
    download_status TEXT,
    downloader_type TEXT,
    downloader_id TEXT,
    local_path TEXT,
    confidence REAL,
    rescrape_count INTEGER
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"CREATE TABLE IF NOT EXISTS datasets ({db_string});")
    conn.commit()
    return conn

def load_from_db():
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM datasets")
    rows = cursor.fetchall()
    
    mapped_entries = {}
    for row in rows:
        row_dict = dict(row)
        entry = DatasetEntry.model_validate(row_dict)
        mapped_entries[entry.iid] = entry
    conn.close()
    return mapped_entries

def save_to_db(state):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for entry in state["sources"].values():
        cursor.execute(f"""
            INSERT OR REPLACE INTO datasets (
                iid, url, potential_urls, title, description, repository, task, annotation_type,
                source, license, point_of_contact, contact_email, number_images,
                dimensions, download_status, downloader_type, downloader_id,
                local_path, confidence, rescrape_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.iid, entry.url, entry.potential_urls, entry.title, entry.description, entry.repository,
            entry.task, entry.annotation_type, entry.source, entry.license_,
            entry.point_of_contact, entry.contact_email, entry.number_images,
            entry.dimensions, entry.download_status, entry.downloader_type,
            entry.downloader_id, entry.local_path, entry.confidence,
            entry.rescrape_count
        ))
    conn.commit()
    conn.close()
