"""AI-powered brief analysis service.

This module defines a function `analyse_brief` that takes a free‑form campaign
brief and returns a structured analysis.  In a production deployment this
function would integrate with a large language model such as OpenAI's GPT
family.  The current implementation uses the `openai` Python SDK if an API key
is configured; otherwise it returns a placeholder analysis.

The structured analysis returned by this function is a JSON string containing
the inferred objectives, target audience, suggested influencer criteria,
content strategies and timeline recommendations.  In the interest of keeping
the skeleton lightweight, the function simply echoes the brief with dummy
labels when no API key is provided.
"""

from __future__ import annotations

import json
import os
from typing import Optional

try:
    import openai
except ImportError:
    openai = None  # type: ignore


async def analyse_brief(brief: str) -> str:
    """Analyse a campaign brief using an LLM.

    If an OpenAI API key is available in the environment variable `OPENAI_API_KEY`
    and the `openai` package is installed, the function sends the brief to the
    GPT‑3.5 Turbo model and returns its response.  Otherwise a fallback analysis
    is returned.

    Args:
        brief: Free‑form text describing the campaign objectives, audience and
            constraints.

    Returns:
        A JSON string containing the structured analysis.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and openai is not None:
        openai.api_key = api_key
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert marketing assistant. Extract the objectives, target "
                    "demographics, budget parameters and influencer selection criteria from the "
                    "following campaign brief. Then suggest appropriate content strategies and a "
                    "high‑level timeline with key milestones. Respond in JSON with keys: "
                    "objectives, target_audience, budget, influencer_criteria, content_strategy, timeline."
                ),
            },
            {"role": "user", "content": brief},
        ]
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.4,
                max_tokens=400,
            )
            content = response.choices[0].message.content
            # ensure the response is valid JSON; if not, wrap it
            try:
                parsed = json.loads(content)
                return json.dumps(parsed)
            except json.JSONDecodeError:
                return json.dumps({"analysis": content})
        except Exception as e:
            # Fallback to dummy analysis on error
            return json.dumps(
                {
                    "error": str(e),
                    "analysis": "AI analysis failed; please check API key or logs.",
                }
            )
    # Fallback analysis for environments without OpenAI access
    return json.dumps(
        {
            "objectives": "Extracted objectives would appear here.",
            "target_audience": "Target demographics inferred from the brief.",
            "budget": "Budget details parsed from the brief.",
            "influencer_criteria": "Suggested influencer attributes.",
            "content_strategy": "High‑level content themes and messaging guidance.",
            "timeline": "Recommended timeline and milestones for the campaign.",
        }
    )