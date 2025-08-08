"""Analytics endpoints for advanced insights.

This router exposes endpoints that perform advanced analysis on
influencer data, such as clustering influencers into segments based on
their follower counts, engagement rates and other numeric metrics.
These insights can help clients identify meaningful groups of
influencers and tailor campaigns accordingly.

The clustering implementation uses scikit‑learn's KMeans algorithm.
Because scikit‑learn is CPU‑bound and synchronous, the computation is
dispatched to a separate thread via ``asyncio.to_thread`` to avoid
blocking the event loop.  Only authenticated users with appropriate
roles can access the analytics endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# Attempt to import external clustering modules; fallback if unavailable
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    import numpy as np
except ImportError:
    StandardScaler = None  # type: ignore
    KMeans = None  # type: ignore
    np = None  # type: ignore



router = APIRouter(prefix="/analytics", tags=["Analytics"])


async def _compute_clusters(data: np.ndarray, k: int) -> Dict[str, Any]:
    

    Parameters
    ----------
    data: np.ndarray
        Array of shape (n_samples, n_features) with numeric features.
    k: int
        Desired number of clusters.

    Returns
    -------
    Dict[str, Any]
        Dictionary mapping cluster labels to summary statistics.
    """
    # Standardise features to zero mean and unit variance
    scaler = StandardScaler()
    X = scaler.fit_transform(data)
    # Fit KMeans
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(X)
    # Build summary
    summary: Dict[str, Dict[str, float | int]] = {}
    for label in range(k):
        idx = np.where(labels == label)[0]
        if idx.size == 0:
            continue
        subset = data[idx]
        summary[str(label)] = {
            "size": int(idx.size),
            "avg_followers": float(np.mean(subset[:, 0])),
            "avg_engagement_rate": float(np.mean(subset[:, 1])),
            "avg_avg_likes": float(np.mean(subset[:, 2])),
            "avg_avg_comments": float(np.mean(subset[:, 3])),
        }
    return {"clusters": summary}


@router.get("/segments")
async def influencer_segments(
    k: int = Query(5, ge=2, le=10, description="Number of clusters to produce"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compute influencer segments using k‑means clustering.

    Only users with admin, client or team_member roles can access this
    endpoint.  Influencers belonging to the caller's tenant are
    included in the analysis.  The numeric features used are
    ``followers``, ``engagement_rate``, ``avg_likes`` and
    ``avg_comments``.  Missing values are filtered out.
    """
    if current_user.role not in {
        RoleEnum.admin,
        RoleEnum.client,
        RoleEnum.team_member,
    }:
        raise HTTPException(status_code=403, detail="Not authorised for analytics")
    # Query influencers for the user's tenant
    result = await session.execute(
        select(
            Influencer.followers,
            Influencer.engagement_rate,
            Influencer.avg_likes,
            Influencer.avg_comments,
        ).where(Influencer.tenant_id == current_user.tenant_id)
    )
    rows = result.all()
    # Filter out rows with missing or zero values
    features: List[List[float]] = []
    for followers, engagement_rate, avg_likes, avg_comments in rows:
        if not followers or not engagement_rate or not avg_likes or not avg_comments:
            continue
        features.append([
            float(followers),
            float(engagement_rate),
            float(avg_likes),
            float(avg_comments),
        ])
    if not features:
        return {"clusters": {}}
    data_array = np.array(features)
    # Dispatch clustering to a thread to avoid blocking
    summary = await asyncio.to_thread(_compute_clusters, data_array, k)
    return summary
