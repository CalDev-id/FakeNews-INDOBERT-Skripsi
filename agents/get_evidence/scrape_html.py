import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")


def scrape_html(url):
    """Scrape halaman menggunakan ScrapingBee."""
    try:
        api_url = "https://app.scrapingbee.com/api/v1/"
        params = {
            "api_key": SCRAPINGBEE_API_KEY,
            "url": url,
            "render_js": "true",
            "block_ads": "true",
            "wait": "2000"
        }

        response = requests.get(api_url, params=params, timeout=25)

        if response.status_code != 200:
            print("ScrapingBee error:", response.text)
            return None

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        judul = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else "Unknown"
        )

        time_tag = soup.find("time")
        tanggal = time_tag.get_text(strip=True) if time_tag else "Unknown"

        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]

        div_candidates = soup.find_all(
            "div", class_=re.compile("(article|content|post|isi|entry)")
        )
        for div in div_candidates:
            paragraphs.extend(
                [p.get_text(" ", strip=True) for p in div.find_all("p")]
            )

        paragraphs = [p for p in paragraphs if len(p) > 50]

        content = (
            "\n".join(paragraphs)
            if paragraphs
            else "Tidak berhasil ekstrak isi artikel"
        )

        return {
            "judul": judul,
            "tanggal": tanggal,
            "sumber": urlparse(url).netloc.replace("www.", ""),
            "link": url,
            "content": content,
        }

    except Exception as e:
        print(f"⚠️ Gagal scrape {url}: {e}")
        return None
