"""SQLite database schema for the Fiverr SERP Analyzer.

Tables: keywords, gigs, sellers, keyword_gig_results, collection_runs, errors.
Uses stable IDs and upserts for resume capability.
"""

import sqlite3
import os
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS collection_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    total_keywords INTEGER,
    completed_keywords INTEGER DEFAULT 0,
    failed_keywords INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS keywords (
    keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    normalized_keyword TEXT NOT NULL,
    first_seen_run_id TEXT,
    last_collected_at TEXT,
    total_results_raw TEXT,
    total_results_parsed INTEGER,
    total_results_state TEXT DEFAULT 'missing',
    total_results_selector TEXT,
    collection_status TEXT DEFAULT 'pending',
    error_message TEXT,
    challenge_paused INTEGER DEFAULT 0,
    FOREIGN KEY (first_seen_run_id) REFERENCES collection_runs(run_id)
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name_normalized TEXT,
    seller_name_raw TEXT,
    seller_profile_url_normalized TEXT UNIQUE,
    seller_profile_url_raw TEXT,
    seller_level_raw TEXT,
    seller_level_normalized TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS gigs (
    gig_id INTEGER PRIMARY KEY AUTOINCREMENT,
    gig_url_normalized TEXT UNIQUE,
    gig_url_raw TEXT,
    gig_fiverr_id TEXT,
    title_raw TEXT,
    title_normalized TEXT,
    title_state TEXT DEFAULT 'missing',
    title_selector TEXT,
    seller_id INTEGER,
    seller_rating_raw TEXT,
    seller_rating_normalized TEXT,
    seller_rating_state TEXT DEFAULT 'missing',
    seller_rating_selector TEXT,
    review_count_raw TEXT,
    review_count_cleaned TEXT,
    review_count_state TEXT DEFAULT 'missing',
    review_count_selector TEXT,
    starting_price_raw TEXT,
    starting_price_normalized TEXT,
    starting_price_state TEXT DEFAULT 'missing',
    starting_price_selector TEXT,
    delivery_time_raw TEXT,
    delivery_time_normalized TEXT,
    delivery_time_state TEXT DEFAULT 'missing',
    delivery_time_selector TEXT,
    badges_raw TEXT,
    badges_normalized TEXT,
    badges_state TEXT DEFAULT 'missing',
    badges_selector TEXT,
    category_raw TEXT,
    category_normalized TEXT,
    category_state TEXT DEFAULT 'missing',
    category_selector TEXT,
    service_tags_raw TEXT,
    service_tags_normalized TEXT,
    service_tags_state TEXT DEFAULT 'missing',
    service_tags_selector TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT,
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
);

CREATE TABLE IF NOT EXISTS keyword_gig_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    keyword_id INTEGER NOT NULL,
    gig_id INTEGER NOT NULL,
    serp_position INTEGER NOT NULL,
    collection_timestamp TEXT NOT NULL,
    card_selector_used TEXT,
    FOREIGN KEY (run_id) REFERENCES collection_runs(run_id),
    FOREIGN KEY (keyword_id) REFERENCES keywords(keyword_id),
    FOREIGN KEY (gig_id) REFERENCES gigs(gig_id),
    UNIQUE(run_id, keyword_id, serp_position)
);

CREATE TABLE IF NOT EXISTS errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    keyword TEXT,
    error_type TEXT,
    error_detail TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES collection_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(collection_status);
CREATE INDEX IF NOT EXISTS idx_gigs_url ON gigs(gig_url_normalized);
CREATE INDEX IF NOT EXISTS idx_gigs_seller ON gigs(seller_id);
CREATE INDEX IF NOT EXISTS idx_sellers_url ON sellers(seller_profile_url_normalized);
CREATE INDEX IF NOT EXISTS idx_results_run ON keyword_gig_results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_keyword ON keyword_gig_results(keyword_id);
CREATE INDEX IF NOT EXISTS idx_errors_run ON errors(run_id);
"""


def get_db_path(db_dir: str = "data") -> str:
    """Get the SQLite database path."""
    Path(db_dir).mkdir(parents=True, exist_ok=True)
    return os.path.join(db_dir, "fiverr_serp.db")


def init_db(db_path: str = None) -> sqlite3.Connection:
    """Initialize the database and return a connection."""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Use autocommit mode so we can manage transactions manually
    conn.isolation_level = None
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
