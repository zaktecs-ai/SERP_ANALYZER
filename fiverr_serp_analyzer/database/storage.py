"""Storage layer for persisting collected SERP data to SQLite.

Handles upserts, transactional commits per keyword, and error logging.
"""

import json
import sqlite3
from datetime import datetime, timezone
from database.models import init_db, get_db_path


class StorageManager:
    """Manages all database operations for the Fiverr SERP Analyzer."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self.conn = init_db(db_path)
        self._in_transaction = False

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # --- Collection Runs ---

    def create_run(self, run_id: str, total_keywords: int) -> bool:
        """Create a new collection run record."""
        try:
            self.conn.execute(
                """INSERT OR REPLACE INTO collection_runs
                   (run_id, started_at, total_keywords, status)
                   VALUES (?, ?, ?, 'running')""",
                (run_id, datetime.now(timezone.utc).isoformat(), total_keywords),
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Error (create_run): {e}")
            return False

    def update_run_status(self, run_id: str, status: str,
                          completed: int = None, failed: int = None):
        """Update run status and counts."""
        try:
            if completed is not None and failed is not None:
                self.conn.execute(
                    """UPDATE collection_runs
                       SET status=?, completed_keywords=?, failed_keywords=?,
                           finished_at=?
                       WHERE run_id=?""",
                    (status, completed, failed,
                     datetime.now(timezone.utc).isoformat(), run_id),
                )
            else:
                self.conn.execute(
                    "UPDATE collection_runs SET status=? WHERE run_id=?",
                    (status, run_id),
                )
            self.conn.commit()
        except Exception as e:
            print(f"DB Error (update_run_status): {e}")

    # --- Keywords ---

    def upsert_keyword(self, keyword: str, run_id: str,
                       collection_result: dict) -> int:
        """Insert or update a keyword record. Returns keyword_id."""
        normalized = keyword.lower().strip()
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self.conn.execute(
                """INSERT INTO keywords
                   (keyword, normalized_keyword, first_seen_run_id,
                    last_collected_at, total_results_raw, total_results_parsed,
                    total_results_state, total_results_selector,
                    collection_status, error_message, challenge_paused)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(keyword) DO UPDATE SET
                    last_collected_at=excluded.last_collected_at,
                    total_results_raw=excluded.total_results_raw,
                    total_results_parsed=excluded.total_results_parsed,
                    total_results_state=excluded.total_results_state,
                    total_results_selector=excluded.total_results_selector,
                    collection_status=excluded.collection_status,
                    error_message=excluded.error_message,
                    challenge_paused=excluded.challenge_paused""",
                (
                    keyword,
                    normalized,
                    run_id,
                    now,
                    collection_result.get("total_results_raw"),
                    collection_result.get("total_results_parsed"),
                    collection_result.get("total_results_state", "missing"),
                    collection_result.get("total_results_selector"),
                    "completed" if not collection_result.get("error") else "failed",
                    collection_result.get("error"),
                    1 if collection_result.get("challenge_paused") else 0,
                ),
            )
            if not self._in_transaction:
                self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"DB Error (upsert_keyword): {e}")
            return -1

    def get_keyword_id(self, keyword: str) -> int:
        """Get the keyword_id for a keyword."""
        normalized = keyword.lower().strip()
        row = self.conn.execute(
            "SELECT keyword_id FROM keywords WHERE normalized_keyword=?",
            (normalized,),
        ).fetchone()
        return row["keyword_id"] if row else None

    # --- Sellers ---

    def upsert_seller(self, gig_data: dict) -> int:
        """Insert or update a seller record. Returns seller_id."""
        profile_url = gig_data.get("seller_profile_url_normalized", "")
        if not profile_url:
            return None

        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = self.conn.execute(
                """INSERT INTO sellers
                   (seller_name_normalized, seller_name_raw,
                    seller_profile_url_normalized, seller_profile_url_raw,
                    seller_level_raw, seller_level_normalized,
                    first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(seller_profile_url_normalized) DO UPDATE SET
                    seller_name_normalized=excluded.seller_name_normalized,
                    seller_name_raw=excluded.seller_name_raw,
                    seller_level_raw=excluded.seller_level_raw,
                    seller_level_normalized=excluded.seller_level_normalized,
                    last_seen_at=excluded.last_seen_at""",
                (
                    gig_data.get("seller_name_normalized"),
                    gig_data.get("seller_name_raw"),
                    profile_url,
                    gig_data.get("seller_profile_url_raw"),
                    gig_data.get("seller_level_raw"),
                    gig_data.get("seller_level_normalized"),
                    now,
                    now,
                ),
            )
            if not self._in_transaction:
                self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"DB Error (upsert_seller): {e}")
            return None

    # --- Gigs ---

    def upsert_gig(self, gig_data: dict, seller_id: int) -> int:
        """Insert or update a gig record. Returns gig_id."""
        url = gig_data.get("url_normalized", "")
        if not url:
            return None

        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = self.conn.execute(
                """INSERT INTO gigs
                   (gig_url_normalized, gig_url_raw, gig_fiverr_id,
                    title_raw, title_normalized, title_state, title_selector,
                    seller_id,
                    seller_rating_raw, seller_rating_normalized,
                    seller_rating_state, seller_rating_selector,
                    review_count_raw, review_count_cleaned,
                    review_count_state, review_count_selector,
                    starting_price_raw, starting_price_normalized,
                    starting_price_state, starting_price_selector,
                    delivery_time_raw, delivery_time_normalized,
                    delivery_time_state, delivery_time_selector,
                    badges_raw, badges_normalized, badges_state, badges_selector,
                    category_raw, category_normalized, category_state, category_selector,
                    service_tags_raw, service_tags_normalized,
                    service_tags_state, service_tags_selector,
                    first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(gig_url_normalized) DO UPDATE SET
                    title_raw=excluded.title_raw,
                    title_normalized=excluded.title_normalized,
                    title_state=excluded.title_state,
                    title_selector=excluded.title_selector,
                    seller_id=excluded.seller_id,
                    seller_rating_raw=excluded.seller_rating_raw,
                    seller_rating_normalized=excluded.seller_rating_normalized,
                    seller_rating_state=excluded.seller_rating_state,
                    seller_rating_selector=excluded.seller_rating_selector,
                    review_count_raw=excluded.review_count_raw,
                    review_count_cleaned=excluded.review_count_cleaned,
                    review_count_state=excluded.review_count_state,
                    review_count_selector=excluded.review_count_selector,
                    starting_price_raw=excluded.starting_price_raw,
                    starting_price_normalized=excluded.starting_price_normalized,
                    starting_price_state=excluded.starting_price_state,
                    starting_price_selector=excluded.starting_price_selector,
                    delivery_time_raw=excluded.delivery_time_raw,
                    delivery_time_normalized=excluded.delivery_time_normalized,
                    delivery_time_state=excluded.delivery_time_state,
                    delivery_time_selector=excluded.delivery_time_selector,
                    badges_raw=excluded.badges_raw,
                    badges_normalized=excluded.badges_normalized,
                    badges_state=excluded.badges_state,
                    badges_selector=excluded.badges_selector,
                    category_raw=excluded.category_raw,
                    category_normalized=excluded.category_normalized,
                    category_state=excluded.category_state,
                    category_selector=excluded.category_selector,
                    service_tags_raw=excluded.service_tags_raw,
                    service_tags_normalized=excluded.service_tags_normalized,
                    service_tags_state=excluded.service_tags_state,
                    service_tags_selector=excluded.service_tags_selector,
                    last_seen_at=excluded.last_seen_at""",
                (
                    url,
                    gig_data.get("url_raw"),
                    gig_data.get("gig_id_normalized"),
                    gig_data.get("title_raw"),
                    gig_data.get("title_normalized"),
                    gig_data.get("title_state", "missing"),
                    gig_data.get("title_selector"),
                    seller_id,
                    gig_data.get("seller_rating_raw"),
                    gig_data.get("seller_rating_normalized"),
                    gig_data.get("seller_rating_state", "missing"),
                    gig_data.get("seller_rating_selector"),
                    gig_data.get("review_count_raw"),
                    gig_data.get("review_count_cleaned"),
                    gig_data.get("review_count_state", "missing"),
                    gig_data.get("review_count_selector"),
                    gig_data.get("starting_price_raw"),
                    gig_data.get("starting_price_normalized"),
                    gig_data.get("starting_price_state", "missing"),
                    gig_data.get("starting_price_selector"),
                    gig_data.get("delivery_time_raw"),
                    gig_data.get("delivery_time_normalized"),
                    gig_data.get("delivery_time_state", "missing"),
                    gig_data.get("delivery_time_selector"),
                    json.dumps(gig_data.get("badges_raw", [])),
                    json.dumps(gig_data.get("badges_normalized", [])),
                    gig_data.get("badges_state", "missing"),
                    gig_data.get("badges_selector"),
                    gig_data.get("category_raw"),
                    gig_data.get("category_normalized"),
                    gig_data.get("category_state", "missing"),
                    gig_data.get("category_selector"),
                    json.dumps(gig_data.get("service_tags_raw", [])),
                    json.dumps(gig_data.get("service_tags_normalized", [])),
                    gig_data.get("service_tags_state", "missing"),
                    gig_data.get("service_tags_selector"),
                    now,
                    now,
                ),
            )
            if not self._in_transaction:
                self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"DB Error (upsert_gig): {e}")
            return None

    # --- Keyword-Gig Results ---

    def insert_result(self, run_id: str, keyword_id: int, gig_id: int,
                      serp_position: int, collection_timestamp: str,
                      card_selector: str = None):
        """Insert a keyword-gig result link."""
        try:
            self.conn.execute(
                """INSERT OR REPLACE INTO keyword_gig_results
                   (run_id, keyword_id, gig_id, serp_position,
                    collection_timestamp, card_selector_used)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, keyword_id, gig_id, serp_position,
                 collection_timestamp, card_selector),
            )
            if not self._in_transaction:
                self.conn.commit()
        except Exception as e:
            print(f"DB Error (insert_result): {e}")

    # --- Errors ---

    def log_error(self, run_id: str, keyword: str, error_type: str,
                  detail: str = ""):
        """Log an error to the errors table."""
        try:
            self.conn.execute(
                """INSERT INTO errors (run_id, keyword, error_type, error_detail, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, keyword, error_type, detail,
                 datetime.now(timezone.utc).isoformat()),
            )
            self.conn.commit()
        except Exception as e:
            print(f"DB Error (log_error): {e}")

    # --- Transactional keyword save ---

    def save_keyword_results(self, run_id: str, keyword: str,
                             collection_result: dict) -> bool:
        """Save all data for a keyword in a single transaction.

        This is the main entry point for persisting collected data.
        Returns True on success.
        """
        self._in_transaction = True
        try:
            # Start explicit transaction
            self.conn.execute("BEGIN")

            # Upsert keyword
            keyword_id = self.upsert_keyword(keyword, run_id, collection_result)
            if keyword_id < 0:
                raise Exception("Failed to upsert keyword")

            # If there was an error, log it and commit
            if collection_result.get("error"):
                self.log_error(run_id, keyword, "collection_error",
                               collection_result["error"])
                self.conn.execute("COMMIT")
                return True

            # Process each gig
            for gig_data in collection_result.get("gigs", []):
                # Upsert seller
                seller_id = self.upsert_seller(gig_data)

                # Upsert gig
                gig_id = self.upsert_gig(gig_data, seller_id)
                if gig_id is None:
                    continue

                # Insert result link
                self.insert_result(
                    run_id=run_id,
                    keyword_id=keyword_id,
                    gig_id=gig_id,
                    serp_position=gig_data.get("serp_position", 0),
                    collection_timestamp=gig_data.get("collection_timestamp", ""),
                    card_selector=gig_data.get("card_selector_used"),
                )

            self.conn.execute("COMMIT")
            return True

        except Exception as e:
            self.conn.execute("ROLLBACK")
            print(f"DB Error (save_keyword_results): {e}")
            self.log_error(run_id, keyword, "db_transaction_error", str(e)[:500])
            return False

        finally:
            self._in_transaction = False

    # --- Query helpers for analysis ---

    def get_keyword_gigs(self, run_id: str, keyword: str) -> list:
        """Get all gigs for a keyword from the latest run."""
        rows = self.conn.execute(
            """SELECT g.*, kgr.serp_position, kgr.collection_timestamp,
                      s.seller_name_normalized, s.seller_level_normalized,
                      s.seller_profile_url_normalized
               FROM gigs g
               JOIN keyword_gig_results kgr ON g.gig_id = kgr.gig_id
               JOIN keywords k ON kgr.keyword_id = k.keyword_id
               LEFT JOIN sellers s ON g.seller_id = s.seller_id
               WHERE kgr.run_id = ? AND k.keyword = ?
               ORDER BY kgr.serp_position""",
            (run_id, keyword),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_keyword_gigs(self, run_id: str) -> list:
        """Get all keyword-gig results for a run."""
        rows = self.conn.execute(
            """SELECT k.keyword, g.title_normalized, g.gig_url_normalized,
                      kgr.serp_position,
                      g.seller_rating_normalized, g.review_count_cleaned,
                      g.starting_price_normalized, g.delivery_time_normalized,
                      s.seller_name_normalized, s.seller_level_normalized,
                      g.title_state, g.seller_rating_state, g.review_count_state,
                      g.starting_price_state
               FROM gigs g
               JOIN keyword_gig_results kgr ON g.gig_id = kgr.gig_id
               JOIN keywords k ON kgr.keyword_id = k.keyword_id
               LEFT JOIN sellers s ON g.seller_id = s.seller_id
               WHERE kgr.run_id = ?
               ORDER BY k.keyword, kgr.serp_position""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_keywords(self, run_id: str = None) -> list:
        """Get all keywords with their collection metadata."""
        if run_id:
            rows = self.conn.execute(
                """SELECT * FROM keywords WHERE first_seen_run_id = ?
                   ORDER BY keyword""",
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM keywords ORDER BY keyword"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_errors(self, run_id: str = None) -> list:
        """Get all logged errors."""
        if run_id:
            rows = self.conn.execute(
                "SELECT * FROM errors WHERE run_id = ? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM errors ORDER BY timestamp"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_run_info(self, run_id: str) -> dict:
        """Get metadata for a collection run."""
        row = self.conn.execute(
            "SELECT * FROM collection_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None