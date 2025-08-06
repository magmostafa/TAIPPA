"""Platform‑specific scrapers for influencer data collection.

Each scraper class encapsulates the logic for fetching and parsing
publicly available influencer information from a specific social media
platform.  These classes rely on the ``requests`` and ``BeautifulSoup``
libraries to perform HTTP requests and parse HTML content.  The
scrapers are designed to be extended with additional parsing logic
and error handling as needed.  They currently focus on extracting
basic profile metrics such as follower counts, bios and usernames.

Note: Real‑world scraping may require API keys, authentication
cookies, proxy rotation and adherence to platform terms of service.
The examples here operate on publicly accessible pages and may
need to be adapted by the user for reliability at scale.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Iterable

from bs4 import BeautifulSoup

from .utils import make_request, rate_limited


class InstagramScraper:
    """Scraper for Instagram public profiles.

    Fetches the HTML of an Instagram profile page and attempts to
    extract the username, full name, follower count, bio and other
    details.  Instagram heavily obfuscates data for unauthenticated
    users, so scraping may be unreliable without login or API access.
    """

    BASE_URL = "https://www.instagram.com/"

    def __init__(self, proxies: Optional[Iterable[str]] = None) -> None:
        self.proxies = proxies

    @rate_limited(1.0)
    def get_profile(self, username: str) -> Optional[Dict[str, object]]:
        url = f"{self.BASE_URL}{username}/"
        resp = make_request(url, proxies=self.proxies)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Extract title text which contains followers info for public pages
        title = soup.find("title")
        if not title:
            return None
        # Example title: "Marques Brownlee (@mkbhd) • Instagram photos and videos"
        name_match = re.match(r"(.+) \(@.+\) • Instagram", title.text.strip())
        full_name = name_match.group(1) if name_match else username
        # Follower count may appear in meta property description
        desc = soup.find("meta", attrs={"property": "og:description"})
        followers = None
        bio = None
        if desc and desc.get("content"):
            # Description contains follower count and posts: "1.4m Followers, 123 Following, 1,234 Posts - See Instagram photos..."
            content = desc["content"]
            match = re.match(r"([\d,.]+)\w* Followers", content)
            if match:
                followers_str = match.group(1).replace(",", "")
                try:
                    followers = int(float(followers_str) * 1000) if "k" in content.lower() else int(followers_str)
                except ValueError:
                    followers = None
        # Bio might appear in meta property for biography
        bio_meta = soup.find("meta", attrs={"property": "og:description"})
        if bio_meta and bio_meta.get("content"):
            bio = bio_meta["content"]
        return {
            "handle": username,
            "name": full_name,
            "platform": "instagram",
            "followers": followers,
            "bio": bio,
        }


class TikTokScraper:
    """Scraper for TikTok creator profiles.

    TikTok pages deliver JSON data embedded in the HTML.  This scraper
    attempts to parse the follower count and bio from that JSON.  If
    data extraction fails, None is returned.
    """

    BASE_URL = "https://www.tiktok.com/@"

    def __init__(self, proxies: Optional[Iterable[str]] = None) -> None:
        self.proxies = proxies

    @rate_limited(1.0)
    def get_profile(self, username: str) -> Optional[Dict[str, object]]:
        url = f"{self.BASE_URL}{username}"
        resp = make_request(url, proxies=self.proxies)
        if resp.status_code != 200:
            return None
        # Search for initial state JSON
        json_match = re.search(r'window.__INIT_PROPS__\s*=\s*(\{.*\});', resp.text)
        if not json_match:
            return None
        import json
        try:
            data = json.loads(json_match.group(1))
            # Navigate to user info (this structure may change over time)
            user_data = next(iter(data.values()))["userInfo"]
            stats = user_data["stats"]
            return {
                "handle": username,
                "name": user_data["user"].get("nickname", username),
                "platform": "tiktok",
                "followers": stats.get("followerCount"),
                "bio": user_data["user"].get("signature"),
            }
        except Exception:
            return None


class YouTubeScraper:
    """Scraper for YouTube channel pages.

    Fetches the HTML of a YouTube channel and attempts to extract the
    subscriber count and description from meta tags.  Note that
    YouTube may block scraping or return 404 for non‑canonical URLs.
    """

    BASE_URL = "https://www.youtube.com/"

    def __init__(self, proxies: Optional[Iterable[str]] = None) -> None:
        self.proxies = proxies

    @rate_limited(1.0)
    def get_profile(self, channel_handle: str) -> Optional[Dict[str, object]]:
        # Channel handles often start with '@'
        url = f"{self.BASE_URL}{channel_handle}"
        resp = make_request(url, proxies=self.proxies)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Subscriber count may be in meta itemprop="interactionCount"
        subs = None
        meta_subs = soup.find("meta", attrs={"itemprop": "interactionCount"})
        if meta_subs and meta_subs.get("content"):
            try:
                subs = int(meta_subs["content"])
            except ValueError:
                subs = None
        # Description in meta name="description"
        desc_meta = soup.find("meta", attrs={"name": "description"})
        desc = desc_meta.get("content") if desc_meta else None
        return {
            "handle": channel_handle,
            "name": channel_handle.lstrip("@"),
            "platform": "youtube",
            "followers": subs,
            "bio": desc,
        }


class TwitterScraper:
    """Scraper for Twitter/X profiles.

    Extracts follower counts and bios from public profile pages.  Twitter
    may block scraping or require authentication; this scraper may
    therefore be unreliable without valid cookies.  Use an API if
    possible.
    """

    BASE_URL = "https://twitter.com/"

    def __init__(self, proxies: Optional[Iterable[str]] = None) -> None:
        self.proxies = proxies

    @rate_limited(1.0)
    def get_profile(self, handle: str) -> Optional[Dict[str, object]]:
        url = f"{self.BASE_URL}{handle}"
        resp = make_request(url, proxies=self.proxies)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Bio and name are in meta tags
        meta_desc = soup.find("meta", attrs={"name": "description"})
        bio = meta_desc.get("content") if meta_desc else None
        # Follower count may appear in meta property="og:description"
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        followers = None
        if og_desc and og_desc.get("content"):
            # Example: "1.5M Followers, 100 Following, 3,000 Posts"
            content = og_desc["content"]
            match = re.match(r"([\d,.]+) Followers", content)
            if match:
                count_str = match.group(1).replace(",", "")
                try:
                    followers = int(float(count_str))
                except ValueError:
                    followers = None
        # Name is in og:title ("Name (@handle) / X")
        og_title = soup.find("meta", attrs={"property": "og:title"})
        name = None
        if og_title and og_title.get("content"):
            name_match = re.match(r"(.+) \(@.+\) /", og_title["content"])
            if name_match:
                name = name_match.group(1)
        return {
            "handle": handle,
            "name": name or handle,
            "platform": "twitter",
            "followers": followers,
            "bio": bio,
        }