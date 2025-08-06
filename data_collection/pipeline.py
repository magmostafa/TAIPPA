"""Data processing and persistence pipeline for influencer profiles.

This module defines functions to normalise, validate and store
influencer data collected by platform scrapers.  It uses the
``sqlite3`` module to interact with the local TAIPPA database and
ensures that the necessary tables exist before inserting or updating
records.  Data validation rules can be extended to enforce quality
standards such as minimum engagement rates or recent activity.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from .utils import rate_limited


def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the TAIPPA SQLite database.

    If the database file does not exist, it will be created along with
    the required tables.  The location of the database file is fixed
    relative to the repository root at ``taippa.db``.
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "taippa.db")
    conn = sqlite3.connect(db_path)
    # Ensure foreign keys are enforced
    conn.execute("PRAGMA foreign_keys = ON;")
    # Initialise tables if necessary
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tenants and influencers tables if absent.

    This helper is similar to the one defined in the population script
    but scoped locally to avoid cross‑imports.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            domain TEXT,
            logo_url TEXT,
            primary_color TEXT,
            secondary_color TEXT,
            site_name TEXT,
            tagline TEXT,
            footer_message TEXT,
            features TEXT,
            custom_css TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS influencers (
            id TEXT PRIMARY KEY,
            handle TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            followers INTEGER,
            engagement_rate REAL,
            bio TEXT,
            topics TEXT,
            country TEXT,
            language TEXT,
            avg_likes INTEGER,
            avg_comments INTEGER,
            audience_country TEXT,
            audience_gender TEXT,
            audience_age TEXT,
            last_updated TEXT,
            created_at TEXT,
            updated_at TEXT,
            tenant_id TEXT NOT NULL,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def get_or_create_tenant(conn: sqlite3.Connection, name: str = "Demo Tenant") -> str:
    """Return the ID of a tenant with the given name, creating it if needed."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    tenant_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO tenants (
            id, name, domain, logo_url, primary_color, secondary_color,
            site_name, tagline, footer_message, features, custom_css,
            created_at, updated_at
        ) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
        """,
        (tenant_id, name, now, now),
    )
    conn.commit()
    return tenant_id


def normalise_profile(profile: Dict[str, object], tenant_id: str) -> Optional[Dict[str, object]]:
    """Validate and normalise a scraped profile dictionary.

    Ensures required fields are present and adds timestamps and tenant
    association.  Returns None if the profile does not meet minimum
    quality criteria (e.g. missing followers).  Extend this function
    with additional validation logic as needed.
    """
    required_fields = {"handle", "name", "platform"}
    if not required_fields.issubset(profile.keys()):
        return None
    # Ensure follower count is present and a positive integer
    followers = profile.get("followers")
    if followers is None or (isinstance(followers, int) and followers <= 0):
        return None
    now = datetime.utcnow().isoformat()
    return {
        "id": uuid.uuid4().hex,
        "handle": profile["handle"].lower(),
        "name": profile["name"],
        "platform": profile["platform"],
        "followers": followers,
        "engagement_rate": profile.get("engagement_rate"),
        "bio": profile.get("bio"),
        "topics": profile.get("topics"),
        "country": profile.get("country"),
        "language": profile.get("language"),
        "avg_likes": profile.get("avg_likes"),
        "avg_comments": profile.get("avg_comments"),
        "audience_country": profile.get("audience_country"),
        "audience_gender": profile.get("audience_gender"),
        "audience_age": profile.get("audience_age"),
        "last_updated": now,
        "created_at": now,
        "updated_at": now,
        "tenant_id": tenant_id,
    }


def upsert_profiles(conn: sqlite3.Connection, profiles: List[Dict[str, object]]) -> None:
    """Insert or update influencer profiles in the database.

    Uses ``INSERT OR REPLACE`` semantics to update existing records with
    the same handle.  Handles are assumed to be unique per platform.
    """
    stmt = (
        """
        INSERT OR REPLACE INTO influencers (
            id, handle, name, platform, followers, engagement_rate, bio,
            topics, country, language, avg_likes, avg_comments,
            audience_country, audience_gender, audience_age,
            last_updated, created_at, updated_at, tenant_id
        ) VALUES (
            :id, :handle, :name, :platform, :followers, :engagement_rate, :bio,
            :topics, :country, :language, :avg_likes, :avg_comments,
            :audience_country, :audience_gender, :audience_age,
            :last_updated, :created_at, :updated_at, :tenant_id
        )
        """
    )
    conn.executemany(stmt, profiles)
    conn.commit()


def process_and_store(raw_profiles: List[Dict[str, object]], tenant_name: str = "Demo Tenant") -> int:
    """Normalise and store raw influencer profiles.

    Opens a database connection, creates the tenant if necessary,
    normalises each profile, filters out invalid entries and inserts
    them into the database.  Returns the number of profiles stored.
    """
    conn = get_db_connection()
    try:
        tenant_id = get_or_create_tenant(conn, tenant_name)
        processed: List[Dict[str, object]] = []
        for profile in raw_profiles:
            norm = normalise_profile(profile, tenant_id)
            if norm:
                processed.append(norm)
        if processed:
            upsert_profiles(conn, processed)
        return len(processed)
    finally:
        conn.close()