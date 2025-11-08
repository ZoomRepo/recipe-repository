"""Login whitelist management for the temporary access gate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import errors, pooling

from .auth import _is_valid_email
from .config import DatabaseConfig


@dataclass(frozen=True)
class WhitelistEntry:
    """Represents an email address allowed to receive login codes."""

    email: str
    added_at: datetime | None = None


class LoginWhitelistRepository:
    """Persistence layer for the login email whitelist."""

    def __init__(self, pool: pooling.MySQLConnectionPool) -> None:
        self._pool = pool

    @classmethod
    def from_config(cls, config: DatabaseConfig) -> "LoginWhitelistRepository":
        pool = pooling.MySQLConnectionPool(
            pool_name=f"{config.pool_name}_whitelist",
            pool_size=config.pool_size,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset="utf8mb4",
            use_unicode=True,
        )
        return cls(pool)

    def list_entries(self) -> List[WhitelistEntry]:
        sql = """
            SELECT email, created_at
            FROM login_email_whitelist
            ORDER BY email ASC
        """
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            connection.close()
        entries: List[WhitelistEntry] = []
        for row in rows or []:
            entries.append(
                WhitelistEntry(
                    email=row["email"],
                    added_at=row.get("created_at"),
                )
            )
        return entries

    def add_email(self, email: str) -> bool:
        normalized = email.lower()
        sql = """
            INSERT INTO login_email_whitelist (email)
            VALUES (%s)
        """
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (normalized,))
                connection.commit()
                return True
            except errors.IntegrityError:
                connection.rollback()
                return False
            finally:
                cursor.close()
        finally:
            connection.close()

    def remove_email(self, email: str) -> bool:
        normalized = email.lower()
        sql = "DELETE FROM login_email_whitelist WHERE email = %s"
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (normalized,))
                connection.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
        finally:
            connection.close()

    def is_allowed(self, email: str) -> bool:
        normalized = email.lower()
        sql = "SELECT 1 FROM login_email_whitelist WHERE email = %s LIMIT 1"
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, (normalized,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        return bool(row)


def register_whitelist_routes(app, repository: LoginWhitelistRepository) -> None:
    """Expose management views for the login whitelist."""

    blueprint = Blueprint("whitelist", __name__, url_prefix="/whitelist")

    @blueprint.route("/", methods=["GET", "POST"])
    def index() -> str:
        if request.method == "POST":
            email = (request.form.get("email") or "").strip()
            if not email:
                flash("Enter an email address to add to the whitelist.", "error")
            elif not _is_valid_email(email):
                flash("Enter a valid email address to whitelist.", "error")
            else:
                if repository.add_email(email):
                    flash(
                        f"Added {email.lower()} to the login whitelist.",
                        "success",
                    )
                else:
                    flash("That email is already on the whitelist.", "error")
            return redirect(url_for("whitelist.index"))

        entries = repository.list_entries()
        return render_template("whitelist/index.html", entries=entries)

    @blueprint.post("/remove")
    def remove() -> str:
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Select an email to remove from the whitelist.", "error")
        else:
            if repository.remove_email(email):
                flash(
                    f"Removed {email.lower()} from the login whitelist.",
                    "success",
                )
            else:
                flash("That email is not currently whitelisted.", "error")
        return redirect(url_for("whitelist.index"))

    app.register_blueprint(blueprint)


__all__: Iterable[str] = [
    "LoginWhitelistRepository",
    "WhitelistEntry",
    "register_whitelist_routes",
]
