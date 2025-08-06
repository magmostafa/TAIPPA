"""Utility functions for web scraping and data collection.

This module provides helper functions to support respectful data
collection, including user‑agent rotation, proxy selection and
rate‑limiting decorators.  It aims to promote ethical scraping by
obeying delays between requests and randomising request headers to
reduce the likelihood of detection.
"""

from __future__ import annotations

import random
import time
from typing import Iterable, Optional, Callable, Any

import requests

# List of common desktop and mobile user agents.  Extend this list as
# needed to mimic diverse clients.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/114.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/94.0 Mobile Safari/537.36",
]


def get_random_user_agent() -> str:
    """Return a random user agent string from the list of known agents."""
    return random.choice(USER_AGENTS)


def rate_limited(min_delay: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to enforce a minimum delay between function calls.

    The decorated function will pause for at least ``min_delay`` seconds
    after each call.  This is useful for respecting rate limits on
    external websites.  Usage::

        @rate_limited(1.0)
        def fetch(...):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        last_call = 0.0

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_call
            elapsed = time.time() - last_call
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)
            result = func(*args, **kwargs)
            last_call = time.time()
            return result

        return wrapper

    return decorator


def make_request(url: str, *, proxies: Optional[Iterable[str]] = None, timeout: int = 10) -> requests.Response:
    """Perform an HTTP GET request with randomised user agent and optional proxies.

    Parameters
    ----------
    url: str
        The target URL to fetch.
    proxies: Optional[Iterable[str]]
        An optional iterable of proxy server URLs.  If provided, a
        proxy will be chosen at random for the request.
    timeout: int
        Timeout in seconds for the HTTP request.

    Returns
    -------
    requests.Response
        The HTTP response object.  Users should check the status code
        and handle errors appropriately.
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = None
    if proxies:
        proxy = random.choice(list(proxies))
        proxy_dict = {"http": proxy, "https": proxy}
    else:
        proxy_dict = None
    response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=timeout)
    return response