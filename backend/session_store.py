"""
Session Store - In-Memory Session Management

Provides thread-safe session storage with automatic cleanup of expired sessions.
Can be upgraded to Redis for multi-instance deployments.
"""

import threading
from datetime import datetime, timedelta
from typing import Optional, Dict
import uuid


class SessionStore:
    """Thread-safe in-memory session storage."""

    def __init__(self, session_lifetime_days: int = 7):
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self.session_lifetime_days = session_lifetime_days

    def create_session(self, email: str) -> str:
        """Create a new session and return session ID."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.session_lifetime_days)

        with self._lock:
            self._sessions[session_id] = {
                "email": email,
                "created_at": now,
                "expires_at": expires_at,
                "last_activity": now
            }

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data by session ID."""
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return None

            # Check if session expired
            if datetime.utcnow() > session["expires_at"]:
                del self._sessions[session_id]
                return None

            # Update last activity
            session["last_activity"] = datetime.utcnow()
            return session.copy()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if session existed."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of deleted sessions."""
        now = datetime.utcnow()
        expired_ids = []

        with self._lock:
            for session_id, session in self._sessions.items():
                if now > session["expires_at"]:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                del self._sessions[session_id]

        return len(expired_ids)

    def get_all_sessions(self) -> Dict[str, dict]:
        """Get all active sessions (for debugging/admin)."""
        with self._lock:
            return self._sessions.copy()

    def session_count(self) -> int:
        """Get count of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session store instance
session_store = SessionStore()
