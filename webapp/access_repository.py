"""Data access helpers for subscription and invite flows."""
from __future__ import annotations

from typing import Any, Dict, Optional

from mysql.connector import pooling


class AccessRepository:
    """Persistence operations for subscriber and invite records."""

    def __init__(self, pool: pooling.MySQLConnectionPool) -> None:
        self._pool = pool

    @classmethod
    def from_pool(cls, pool: pooling.MySQLConnectionPool) -> "AccessRepository":
        return cls(pool)

    def add_subscriber(self, email: str) -> None:
        """Store *email* in the subscribers table, ignoring duplicates."""

        sql = (
            "INSERT INTO subscribers (email) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE email = VALUES(email)"
        )
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (email,))
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def get_invited_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Return invited user details for *email* or ``None``."""

        sql = (
            "SELECT id, email, access_code, code_generated_at, device_id "
            "FROM invited_users WHERE email = %s"
        )
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql, (email,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        return row

    def save_access_code(self, invited_user_id: int, access_code: str) -> None:
        """Persist *access_code* for the invited user."""

        sql = (
            "UPDATE invited_users SET access_code = %s, code_generated_at = NOW() "
            "WHERE id = %s"
        )
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (access_code, invited_user_id))
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def clear_access_code(self, invited_user_id: int) -> None:
        """Remove the stored access code for the invited user."""

        sql = "UPDATE invited_users SET access_code = NULL, code_generated_at = NULL WHERE id = %s"
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (invited_user_id,))
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def save_device_id(self, invited_user_id: int, device_id: str) -> None:
        """Store the trusted *device_id* for the invited user."""

        sql = "UPDATE invited_users SET device_id = %s WHERE id = %s"
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (device_id, invited_user_id))
                connection.commit()
            finally:
                cursor.close()
        finally:
            connection.close()

    def get_invited_user_by_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Return invited user data with matching *device_id* or ``None``."""

        sql = (
            "SELECT id, email, access_code, code_generated_at, device_id "
            "FROM invited_users WHERE device_id = %s"
        )
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql, (device_id,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        return row
