import sqlite3
import uuid
from typing import Dict, Any, List, Optional


class OAuthAccountMixin:
    """CRUD for OAuth accounts (ChatGPT/OpenAI subscription auth).
    Requires self._connect() from the host class."""

    def get_oauth_accounts(self) -> List[Dict[str, Any]]:
        """Return all OAuth accounts ordered by priority."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM oauth_accounts ORDER BY priority ASC, created_at ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_oauth_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM oauth_accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_oauth_account_by_email(self, email: str, provider: str = 'chatgpt') -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM oauth_accounts WHERE email = ? AND provider = ?",
                (email, provider)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_oauth_account(self, email: str, refresh_token: str, access_token: str = None,
                             expires_at: int = None, plan_type: str = 'plus',
                             provider: str = 'chatgpt') -> Dict[str, Any]:
        """Create or update an OAuth account. If email+provider exists, update tokens."""
        existing = self.get_oauth_account_by_email(email, provider)
        if existing:
            return self.update_oauth_tokens(existing['id'], refresh_token, access_token, expires_at)

        # Auto-assign next priority
        accounts = self.get_oauth_accounts()
        next_priority = len(accounts)

        account_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO oauth_accounts (id, email, provider, refresh_token, access_token,
                    expires_at, plan_type, status, enabled, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 1, ?)
            """, (account_id, email, provider, refresh_token, access_token, expires_at, plan_type, next_priority))
            conn.commit()
        return self.get_oauth_account(account_id)

    def update_oauth_tokens(self, account_id: str, refresh_token: str = None,
                            access_token: str = None, expires_at: int = None) -> Dict[str, Any]:
        with self._connect() as conn:
            updates = ["updated_at = CURRENT_TIMESTAMP"]
            params = []
            if refresh_token is not None:
                updates.append("refresh_token = ?")
                params.append(refresh_token)
            if access_token is not None:
                updates.append("access_token = ?")
                params.append(access_token)
            if expires_at is not None:
                updates.append("expires_at = ?")
                params.append(expires_at)
            params.append(account_id)
            conn.execute(
                f"UPDATE oauth_accounts SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
        return self.get_oauth_account(account_id)

    def update_oauth_status(self, account_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE oauth_accounts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, account_id)
            )
            conn.commit()

    def set_oauth_enabled(self, account_id: str, enabled: bool) -> None:
        """Enable or disable an OAuth account."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE oauth_accounts SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (1 if enabled else 0, account_id)
            )
            conn.commit()

    def set_oauth_priority(self, account_id: str, priority: int) -> None:
        """Set priority for an OAuth account (lower = higher priority)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE oauth_accounts SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (priority, account_id)
            )
            conn.commit()

    def delete_oauth_account(self, account_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM oauth_accounts WHERE id = ?", (account_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_active_oauth_accounts(self, provider: str = 'chatgpt') -> List[Dict[str, Any]]:
        """Return enabled+active accounts ordered by priority."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM oauth_accounts
                   WHERE provider = ? AND status = 'active' AND enabled = 1
                   ORDER BY priority ASC, created_at ASC""",
                (provider,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_next_available_oauth_account(self, provider: str = 'chatgpt',
                                          exclude_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        """Return next available account for fallback, excluding given IDs."""
        accounts = self.get_active_oauth_accounts(provider)
        exclude = set(exclude_ids or [])
        for acc in accounts:
            if acc['id'] not in exclude:
                return acc
        return None
