"""
Script to populate the TAIPPA SQLite database with synthetic influencer
profiles without relying on the SQLAlchemy ORM.

This script creates a local SQLite database file at ``taippa.db`` (in the
repository root) if it does not already exist.  It then ensures the
``tenants`` and ``influencers`` tables exist with schemas matching the
models defined in ``taippa/taippa/models.py``.  A default tenant named
``Demo Tenant`` is created if no tenant is present.  Finally, the script
generates 300 realistic influencer profiles across five marketing
categories: fashion & beauty, technology & gaming, health & fitness,
food & cooking and travel & lifestyle.  Each category is populated with
60 influencers whose attributes (followers, engagement rates, topics,
locations, etc.) are sampled from realistic ranges.  All influencers
are associated with the default tenant.

This script is designed to run in environments where SQLAlchemy is not
available.  It uses Python's built-in ``sqlite3`` module to interact
with the database.  You can execute this script directly with:

  python scripts/populate_influencers_sqlite.py

After running, the ``taippa.db`` file will contain the generated
influencer data.  The TAIPPA application will automatically detect and
use this database when ``DATABASE_URL`` is unset (the default).
"""

from __future__ import annotations

import os
import sqlite3
import uuid
import random
from datetime import datetime
from typing import Dict, List, Tuple


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create the tenants and influencers tables if they do not exist.

    The schema mirrors the ORM models defined in ``taippa/taippa/models.py``.
    The ``tenants`` table stores branding and configuration fields for
    white-label customisation.  The ``influencers`` table stores
    enriched influencer profiles including social metrics and
    demographics.  Foreign key support is enabled on the connection.
    """
    conn.execute("PRAGMA foreign_keys = ON;")
    # Create tenants table
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
    # Create influencers table
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


def get_or_create_default_tenant(conn: sqlite3.Connection) -> str:
    """Retrieve the ID of the first tenant or create a default one.

    If the ``tenants`` table is empty, a new tenant with the name
    ``Demo Tenant`` is inserted.  Returns the tenant's ID.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants LIMIT 1;")
    row = cur.fetchone()
    if row:
        return row[0]
    # Create a new tenant
    tenant_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO tenants (
            id, name, domain, logo_url, primary_color, secondary_color,
            site_name, tagline, footer_message, features, custom_css,
            created_at, updated_at
        ) VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
        """,
        (tenant_id, "Demo Tenant", now, now),
    )
    conn.commit()
    return tenant_id


def choose_weighted(options: List[Tuple[str, float]]) -> str:
    """Return one option from a list of (value, weight) pairs using random weights."""
    total = sum(weight for _, weight in options)
    r = random.uniform(0, total)
    upto = 0
    for value, weight in options:
        if upto + weight >= r:
            return value
        upto += weight
    # Fallback in case of rounding errors
    return options[-1][0]


def generate_influencers(tenant_id: str) -> List[Dict[str, object]]:
    """Generate a list of influencer dictionaries across all categories.

    Each influencer dictionary contains values matching the columns of
    the ``influencers`` table.  The generation logic is based on
    realistic ranges for follower counts, engagement rates, topics and
    demographics for five marketing verticals.  All generated
    influencers share the supplied ``tenant_id``.
    """
    influencers: List[Dict[str, object]] = []
    categories: Dict[str, Dict] = {
        "fashion_beauty": {
            "count": 60,
            "follower_range": (10_000, 2_000_000),
            "locations": [
                ("United States", "en"),
                ("United Kingdom", "en"),
                ("France", "fr"),
                ("Italy", "it"),
                ("Brazil", "pt"),
                ("South Korea", "ko"),
            ],
            "topics": [
                "streetwear", "luxury fashion", "skincare", "makeup tutorials",
                "vintage", "minimalist fashion", "plus size", "men's fashion",
            ],
            "bios": [
                "Fashion lover sharing daily #OOTD and style inspo.",
                "Makeup artist & beauty blogger. Reviews and tutorials.",
                "Skincare obsessed. Honest reviews and routines.",
                "Luxury fashion curator. Showing my favourite designer pieces.",
                "Streetwear enthusiast. Sneakers, hoodies and more.",
            ],
        },
        "technology_gaming": {
            "count": 60,
            "follower_range": (25_000, 5_000_000),
            "locations": [
                ("United States", "en"),
                ("United Kingdom", "en"),
                ("Germany", "de"),
                ("Japan", "ja"),
                ("Canada", "en"),
                ("South Korea", "ko"),
            ],
            "topics": [
                "mobile reviews", "PC gaming", "crypto", "blockchain",
                "AI", "machine learning", "hardware reviews", "programming",
            ],
            "bios": [
                "Tech reviewer sharing insights on the latest gadgets.",
                "Full‑time streamer & gaming enthusiast.",
                "Crypto and blockchain educator. Explaining DeFi & NFTs.",
                "AI researcher making complex topics accessible.",
                "PC builder & hardware geek. Benchmarks and builds.",
            ],
        },
        "health_fitness": {
            "count": 60,
            "follower_range": (15_000, 3_000_000),
            "locations": [
                ("United States", "en"),
                ("Australia", "en"),
                ("United Kingdom", "en"),
                ("Canada", "en"),
                ("Sweden", "sv"),
            ],
            "topics": [
                "yoga", "bodybuilding", "nutrition", "mental health",
                "crossfit", "running", "sports science", "meditation",
            ],
            "bios": [
                "Certified personal trainer helping you reach your goals.",
                "Yoga teacher sharing flows and mindfulness tips.",
                "Nutrition coach. Healthy recipes and meal plans.",
                "Mental health advocate & wellness blogger.",
                "Athlete & sports science nerd. Training tips & recovery.",
            ],
        },
        "food_cooking": {
            "count": 60,
            "follower_range": (20_000, 4_000_000),
            "locations": [
                ("Italy", "it"),
                ("Mexico", "es"),
                ("United States", "en"),
                ("Japan", "ja"),
                ("Spain", "es"),
                ("India", "hi"),
            ],
            "topics": [
                "baking", "healthy eating", "ethnic cuisines", "restaurant reviews",
                "vegan", "quick recipes", "street food", "food photography",
            ],
            "bios": [
                "Home cook sharing family recipes with a modern twist.",
                "Baker & cake decorator. Sweet treats all day.",
                "Exploring the world's cuisines one dish at a time.",
                "Restaurant critic & foodie. Honest reviews.",
                "Vegan chef making plant‑based meals delicious.",
            ],
        },
        "travel_lifestyle": {
            "count": 60,
            "follower_range": (30_000, 6_000_000),
            "locations": [
                ("France", "fr"),
                ("Thailand", "th"),
                ("United States", "en"),
                ("South Africa", "en"),
                ("Brazil", "pt"),
                ("Australia", "en"),
            ],
            "topics": [
                "luxury travel", "budget backpacking", "solo travel", "family travel",
                "adventure", "city guides", "cultural experiences", "digital nomad",
            ],
            "bios": [
                "Travel photographer capturing the beauty of the world.",
                "Digital nomad exploring hidden gems & local culture.",
                "Luxury travel advisor. Hotels, resorts and experiences.",
                "Backpacker sharing budget travel tips & tricks.",
                "Family of four navigating the globe together.",
            ],
        },
    }

    # Platform distribution: 60% Instagram, 25% TikTok, 15% YouTube
    platform_weights: List[Tuple[str, float]] = [
        ("instagram", 0.6),
        ("tiktok", 0.25),
        ("youtube", 0.15),
    ]

    # Helper lists for generating names
    first_names = [
        "Alex", "Sam", "Jordan", "Taylor", "Chris", "Jamie",
        "Morgan", "Casey", "Riley", "Dana", "Leo", "Mia", "Sofia", "Lucas",
        "Ananya", "Ravi", "Luisa", "Giulia", "Yuki", "Minho",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Martinez", "Davis", "Lopez", "Kim", "Lee", "Patel", "Khan", "Singh",
        "Rossi", "Bianchi", "Nakamura", "Kobayashi", "Fernandez", "Silva",
    ]

    # Track used handles to ensure uniqueness across all categories
    used_handles: set[str] = set()

    # Generate influencers per category
    for cat_key, cfg in categories.items():
        count = cfg["count"]
        min_followers, max_followers = cfg["follower_range"]
        locations = cfg["locations"]
        topics_pool = cfg["topics"]
        bios = cfg["bios"]
        for _ in range(count):
            # Generate a unique ID
            influencer_id = str(uuid.uuid4())
            # Name
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            # Generate a unique handle.  If a collision occurs, keep trying
            # different suffixes until a unique handle is found.  This loop
            # should rarely iterate more than once given the large name and
            # suffix space.
            base_handle = name.lower().replace(" ", "")
            while True:
                suffix = random.choice([
                    "",
                    str(random.randint(1, 9999)),
                    "official",
                    "tv",
                    "blog",
                ])
                handle = f"{base_handle}{suffix}"
                if handle not in used_handles:
                    used_handles.add(handle)
                    break
            # Platform
            platform = choose_weighted(platform_weights)
            # Followers
            followers = random.randint(min_followers, max_followers)
            # Engagement rate based on follower tier
            if followers < 50_000:
                engagement_rate = round(random.uniform(1.5, 4.0), 2)
            elif followers < 200_000:
                engagement_rate = round(random.uniform(1.0, 3.0), 2)
            elif followers < 1_000_000:
                engagement_rate = round(random.uniform(0.5, 2.0), 2)
            else:
                engagement_rate = round(random.uniform(0.3, 1.2), 2)
            # Location & language
            country, language = random.choice(locations)
            # Topics: pick 1–3 topics
            topics = ", ".join(random.sample(topics_pool, k=random.randint(1, 3)))
            # Bio
            bio = random.choice(bios)
            # Average likes & comments (approx engagement_rate * followers)
            avg_likes = int(followers * (engagement_rate / 100) * random.uniform(0.8, 1.2))
            avg_comments = int(avg_likes * random.uniform(0.02, 0.05))
            # Audience demographics
            audience_country = country
            # Gender distribution with category biases
            if cat_key == "fashion_beauty":
                gender_split = random.choice([
                    "80% female, 20% male", "70% female, 30% male", "60% female, 40% male"
                ])
            elif cat_key == "technology_gaming":
                gender_split = random.choice([
                    "70% male, 30% female", "80% male, 20% female", "60% male, 40% female"
                ])
            elif cat_key == "health_fitness":
                gender_split = random.choice([
                    "50% female, 50% male", "60% female, 40% male", "40% female, 60% male"
                ])
            elif cat_key == "food_cooking":
                gender_split = random.choice([
                    "60% female, 40% male", "55% female, 45% male", "50% female, 50% male"
                ])
            else:  # travel_lifestyle
                gender_split = random.choice([
                    "50% female, 50% male", "55% female, 45% male", "45% female, 55% male"
                ])
            audience_age = random.choice(["18-24", "25-34", "35-44", "18-34"])
            now = datetime.utcnow().isoformat()
            influencers.append({
                "id": influencer_id,
                "handle": handle,
                "name": name,
                "platform": platform,
                "followers": followers,
                "engagement_rate": engagement_rate,
                "bio": bio,
                "topics": topics,
                "country": country,
                "language": language,
                "avg_likes": avg_likes,
                "avg_comments": avg_comments,
                "audience_country": audience_country,
                "audience_gender": gender_split,
                "audience_age": audience_age,
                "last_updated": now,
                "created_at": now,
                "updated_at": now,
                "tenant_id": tenant_id,
            })
    return influencers


def insert_influencers(conn: sqlite3.Connection, influencers: List[Dict[str, object]]) -> None:
    """Bulk insert influencer records into the database.

    Uses executemany for efficiency.  Duplicate handles will cause an
    integrity error due to the unique constraint, but the random
    generation logic aims to avoid collisions.  If duplicates occur,
    the caller should regenerate the dataset or adjust handle logic.
    """
    cur = conn.cursor()
    # Prepare insertion statement
    stmt = (
        """
        INSERT INTO influencers (
            id, handle, name, platform, followers, engagement_rate, bio,
            topics, country, language, avg_likes, avg_comments,
            audience_country, audience_gender, audience_age,
            last_updated, created_at, updated_at, tenant_id
        ) VALUES (
            :id, :handle, :name, :platform, :followers, :engagement_rate, :bio,
            :topics, :country, :language, :avg_likes, :avg_comments,
            :audience_country, :audience_gender, :audience_age,
            :last_updated, :created_at, :updated_at, :tenant_id
        );
        """
    )
    cur.executemany(stmt, influencers)
    conn.commit()


def main() -> None:
    # Determine database path (relative to repository root)
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "taippa.db")
    # Connect to SQLite database (creates file if missing)
    conn = sqlite3.connect(db_path)
    try:
        ensure_tables(conn)
        tenant_id = get_or_create_default_tenant(conn)
        influencers = generate_influencers(tenant_id)
        insert_influencers(conn, influencers)
        print(f"Inserted {len(influencers)} influencer records into {db_path} for tenant {tenant_id}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()