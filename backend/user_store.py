"""
User Store - Persistent user management with admin approval flow.

Admin emails are defined via the ADMIN_EMAILS environment variable and are
always approved. All other users must be approved by an admin.
"""

import json
import os
import threading
from pathlib import Path
from typing import List

DATA_DIR = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"


class UserStore:
    """Thread-safe persistent user store backed by a JSON file."""

    def __init__(self):
        self._lock = threading.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if USERS_FILE.exists():
            with open(USERS_FILE, 'r') as f:
                self._data = json.load(f)
        else:
            self._data = {"approved": [], "pending": [], "denied": []}

    def _save(self):
        with open(USERS_FILE, 'w') as f:
            json.dump(self._data, f, indent=2)

    def _get_admin_emails(self) -> List[str]:
        raw = os.getenv("ADMIN_EMAILS", "")
        return [e.strip().lower() for e in raw.split(",") if e.strip()]

    def is_admin(self, email: str) -> bool:
        return email.lower() in self._get_admin_emails()

    def is_approved(self, email: str) -> bool:
        email_lower = email.lower()
        with self._lock:
            return email_lower in self._get_admin_emails() or email_lower in self._data["approved"]

    def request_access(self, email: str) -> str:
        """Submit an access request. Returns 'approved', 'pending', or 'denied'."""
        email_lower = email.lower()
        with self._lock:
            if email_lower in self._get_admin_emails() or email_lower in self._data["approved"]:
                return "approved"
            if email_lower in self._data["denied"]:
                return "denied"
            if email_lower not in self._data["pending"]:
                self._data["pending"].append(email_lower)
                self._save()
            return "pending"

    def get_pending_requests(self) -> List[str]:
        with self._lock:
            return list(self._data["pending"])

    def approve(self, email: str) -> bool:
        email_lower = email.lower()
        with self._lock:
            if email_lower in self._data["pending"]:
                self._data["pending"].remove(email_lower)
                if email_lower not in self._data["approved"]:
                    self._data["approved"].append(email_lower)
                self._save()
                return True
            return False

    def deny(self, email: str) -> bool:
        email_lower = email.lower()
        with self._lock:
            if email_lower in self._data["pending"]:
                self._data["pending"].remove(email_lower)
                if email_lower not in self._data["denied"]:
                    self._data["denied"].append(email_lower)
                self._save()
                return True
            return False


user_store = UserStore()
