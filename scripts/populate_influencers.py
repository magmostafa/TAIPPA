"""
Populate the TAIPPA database with synthetic influencer profiles.

This script generates 300 realistic influencer records across five
categories (fashion & beauty, technology & gaming, health & fitness,
food & cooking, travel & lifestyle).  It uses randomised data within
category‑specific ranges to produce authentic follower counts, engagement
rates, demographic details, bios and topics.  The generated influencers
are associated with the first tenant in the database; if no tenant
exists, a default one is created.

Run this script using:

  python scripts/populate_influencers.py

Ensure that the `DATABASE_URL` environment variable points to your
database (defaults to sqlite file ./taippa.db).  The script uses
SQLAlchemy's async engine and session factory defined in
`taippa/taippa/database.py`.
"""

import asyncio
import os
import sys
import random
from datetime import datetime
from typing import List, Dict, Tuple


# Add the repository root to sys.path to allow relative imports when executed
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from taippa.taippa.database import engine, async_session_factory, Base
from taippa.taippa.models import Tenant, Influencer
from sqlalchemy import select


def choose_weighted(options: List[Tuple[str, float]]) -> str:
    """Return one option from a list of (value, weight) pairs."""
    total = sum(weight for _, weight in options)
    r = random.uniform(0, total)
    upto = 0
    for value, weight in options:
        if upto + weight >= r:
            return value
        upto += weight
    # fallback
    return options[-1][0]


async def populate() -> None:
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        # Fetch or create a tenant
        result = await session.execute(select(Tenant))
        tenant = result.scalars().first()
        if not tenant:
            tenant = Tenant(name="Demo Tenant")
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)

        # Define categories and their parameters
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
        platform_weights = [("instagram", 0.6), ("tiktok", 0.25), ("youtube", 0.15)]

        total_created = 0

        for cat_key, cfg in categories.items():
            count = cfg["count"]
            min_followers, max_followers = cfg["follower_range"]
            locations = cfg["locations"]
            topics_pool = cfg["topics"]
            bios = cfg["bios"]
            for _ in range(count):
                # Name generation: pick random first and last names with cultural diversity
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
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                # Handle generation: combine lowercase name and random number or word
                handle_base = name.lower().replace(" ", "")
                suffix = random.choice(["", str(random.randint(1, 9999)), "official", "tv", "blog"])
                handle = f"{handle_base}{suffix}"
                # Platform
                platform = choose_weighted(platform_weights)
                # Followers and engagement
                followers = random.randint(min_followers, max_followers)
                # Determine tier to derive engagement rate
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
                # Topics: pick 1‑3 unique topics
                topics = ", ".join(random.sample(topics_pool, k=random.randint(1, 3)))
                # Bio
                bio = random.choice(bios)
                # Average likes & comments based on engagement
                avg_likes = int(followers * (engagement_rate / 100) * random.uniform(0.8, 1.2))
                avg_comments = int(avg_likes * random.uniform(0.02, 0.05))
                # Audience demographics (simplified)
                audience_country = country
                # Gender distribution: random but biased by category
                if cat_key == "fashion_beauty":
                    gender_split = random.choice(["80% female, 20% male", "70% female, 30% male", "60% female, 40% male"])
                elif cat_key == "technology_gaming":
                    gender_split = random.choice(["70% male, 30% female", "80% male, 20% female", "60% male, 40% female"])
                elif cat_key == "health_fitness":
                    gender_split = random.choice(["50% female, 50% male", "60% female, 40% male", "40% female, 60% male"])
                elif cat_key == "food_cooking":
                    gender_split = random.choice(["60% female, 40% male", "55% female, 45% male", "50% female, 50% male"])
                else:
                    gender_split = random.choice(["50% female, 50% male", "55% female, 45% male", "45% female, 55% male"])
                audience_age = random.choice(["18-24", "25-34", "35-44", "18-34"])
                # Create influencer
                influencer = Influencer(
                    handle=handle,
                    name=name,
                    platform=platform,
                    followers=followers,
                    engagement_rate=engagement_rate,
                    bio=bio,
                    topics=topics,
                    country=country,
                    language=language,
                    avg_likes=avg_likes,
                    avg_comments=avg_comments,
                    audience_country=audience_country,
                    audience_gender=gender_split,
                    audience_age=audience_age,
                    last_updated=datetime.utcnow(),
                    tenant_id=tenant.id,
                )
                session.add(influencer)
                total_created += 1
            # end for
        # commit all
        await session.commit()
        print(f"Created {total_created} influencer profiles for tenant {tenant.name}")


if __name__ == "__main__":
    asyncio.run(populate())