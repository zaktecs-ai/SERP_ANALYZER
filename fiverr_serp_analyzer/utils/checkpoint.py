"""Checkpoint and resume functionality for the Fiverr SERP Analyzer."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class CheckpointManager:
    """Manages per-keyword completion status for resume capability."""

    def __init__(self, checkpoint_file: str = "data/checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load checkpoint data from disk."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"completed": {}, "failed": {}, "run_id": None, "last_updated": None}

    def _save(self):
        """Persist checkpoint data to disk."""
        Path(os.path.dirname(self.checkpoint_file)).mkdir(parents=True, exist_ok=True)
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def set_run_id(self, run_id: str):
        """Set the current run ID."""
        self.data["run_id"] = run_id
        self._save()

    def is_completed(self, keyword: str) -> bool:
        """Check if a keyword has been completed."""
        return keyword.lower().strip() in self.data["completed"]

    def is_failed(self, keyword: str) -> bool:
        """Check if a keyword previously failed."""
        return keyword.lower().strip() in self.data["failed"]

    def mark_completed(self, keyword: str, gig_count: int = 0):
        """Mark a keyword as successfully completed."""
        key = keyword.lower().strip()
        self.data["completed"][key] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gig_count": gig_count,
        }
        # Remove from failed if present
        self.data["failed"].pop(key, None)
        self._save()

    def mark_failed(self, keyword: str, reason: str = ""):
        """Mark a keyword as failed."""
        key = keyword.lower().strip()
        self.data["failed"][key] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        self._save()

    def get_pending_keywords(self, all_keywords: list, force: bool = False,
                             resume: bool = False) -> list:
        """Filter keywords to only those that need processing.

        Args:
            all_keywords: Full list of keywords.
            force: If True, reprocess all keywords.
            resume: If True, retry failed keywords as well.

        Returns:
            List of keywords that still need processing.
        """
        if force:
            return list(all_keywords)

        pending = []
        for kw in all_keywords:
            key = kw.lower().strip()
            if self.is_completed(key):
                continue
            if not resume and self.is_failed(key):
                continue
            pending.append(kw)
        return pending

    def clear(self):
        """Clear all checkpoint data."""
        self.data = {"completed": {}, "failed": {}, "run_id": None, "last_updated": None}
        self._save()