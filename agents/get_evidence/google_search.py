import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")

BAD_EXT = [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".mp4"]
SOCIAL_MEDIA_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "fb.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "threads.net",
    "youtube.com",
    "youtu.be"
    "kaggle.com"
    "huggingface.co"
]


def google_search(query, total_results=20):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    results = []
    start = 1

    while len(results) < total_results:
        num = min(10, total_results - len(results))

        try:
            res = service.cse().list(
                q=query,
                cx=CSE_ID,
                num=num,
                start=start
            ).execute()
        except Exception as e:
            print(f"⚠️ Google CSE error: {e}")
            break

        items = res.get("items", [])
        if not items:
            break

        for item in items:
            url = item["link"].split("?")[0].lower()

            domain = urlparse(item["link"]).netloc.replace("www.", "").lower()

            # Skip social media
            if any(domain.endswith(sm) for sm in SOCIAL_MEDIA_DOMAINS):
                continue

            # Skip file extension
            if any(url.endswith(ext) for ext in BAD_EXT):
                continue

            results.append(item["link"])

        start += num

    return results

