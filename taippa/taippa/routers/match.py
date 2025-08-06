"""AI-powered matchmaking endpoints.

This router implements a simple, multi-factor influencer recommendation
algorithm.  It calculates a compatibility score between a brand and each
influencer based on semantic similarity of textual fields and basic
engagement metrics.  The scoring logic is designed to be a placeholder
for more sophisticated AI models (e.g. OpenAI embeddings) but still
provides useful recommendations without external dependencies.
"""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Brand, Influencer, User
from ..auth import get_current_active_user


router = APIRouter(prefix="/match", tags=["matchmaking"])


def tokenize(text: str) -> List[str]:
    """Simple tokenizer that lowercases and splits on non-alphabetic characters.

    This function removes very short tokens and a small list of stop words to
    improve similarity calculations.  It can be replaced with a more
    sophisticated NLP pipeline as needed.
    """
    if not text:
        return []
    import re
    tokens = re.split(r"\W+", text.lower())
    stop_words = {"the", "and", "for", "with", "a", "an", "of", "in", "to", "on"}
    return [t for t in tokens if t and t not in stop_words and len(t) > 2]


@router.get("/brand/{brand_id}", response_model=List[Dict[str, Any]])
async def match_influencers_for_brand(
    brand_id: str,
    top_n: int = Query(5, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Return the top influencer matches for a given brand.

    The algorithm computes a compatibility score for each influencer in the
    current user's tenant.  Scores are a weighted combination of semantic
    similarity between brand and influencer text and engagement metrics.  The
    result includes a human-readable explanation for each score.

    The endpoint requires that the requested brand belongs to the same
    tenant as the requesting user.  Non-admin users cannot access brands
    outside their tenant.  The number of results returned can be controlled
    with the `top_n` query parameter.
    """
    # Retrieve brand and validate access
    brand = await session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    if brand.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Assemble a corpus for the brand
    brand_text_parts = [brand.name or "", brand.description or "", brand.industry or "", brand.target_audience or ""]
    brand_tokens = set(tokenize(" ".join(brand_text_parts)))

    # Fetch influencers for the same tenant
    result = await session.execute(select(Influencer).where(Influencer.tenant_id == current_user.tenant_id))
    influencers = result.scalars().all()
    if not influencers:
        return []

    # Determine maximum followers to normalise engagement scores
    max_followers = max((inf.followers or 0) for inf in influencers) or 1

    recommendations: List[Dict[str, Any]] = []
    for inf in influencers:
        # Compose influencer text
        inf_text_parts = [inf.name or "", inf.handle or "", inf.platform or ""]
        inf_tokens = set(tokenize(" ".join(inf_text_parts)))
        # Jaccard similarity for semantics
        union = brand_tokens | inf_tokens
        intersection = brand_tokens & inf_tokens
        semantic_score = len(intersection) / len(union) if union else 0.0
        # Engagement score: normalise followers and engagement rate
        followers_norm = (inf.followers or 0) / max_followers
        engagement_norm = (inf.engagement_rate or 0) / 100
        engagement_score = 0.5 * followers_norm + 0.5 * engagement_norm
        # Overall weighted score
        overall_score = 0.6 * semantic_score + 0.4 * engagement_score
        # Build explanation string
        explanation = (
            f"Semantic similarity: {semantic_score:.2f}, "
            f"Engagement: {engagement_score:.2f} (followers {followers_norm:.2f}, engagement rate {engagement_norm:.2f})"
        )
        recommendations.append({
            "influencer_id": inf.id,
            "name": inf.name,
            "handle": inf.handle,
            "platform": inf.platform,
            "followers": inf.followers,
            "engagement_rate": inf.engagement_rate,
            "score": round(overall_score, 4),
            "explanation": explanation,
        })
    # Sort recommendations by descending score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:top_n]